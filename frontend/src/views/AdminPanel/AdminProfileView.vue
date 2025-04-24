<template>
	<div class="admin-profile">
		<h1>Админ-панель: Редактирование профиля</h1>

		<!-- Форма отображения и редактирования данных -->
		<div class="profile-info">
			<div class="info-item" v-for="(field, key) in editableFields" :key="key">
				<label :for="key">{{ field.label }}:</label>
				<div class="info-display" v-if="!field.editing">
					<template v-if="key === 'avatar'">
						<img v-if="profile[key]" :src="apiBaseUrl + profile[key].url" class="avatar-preview" alt="Аватар">
						<span v-else>Аватар не установлен</span>
					</template>
					<template v-else-if="key === 'rating'">
						<span>{{ profile[key] ?? 0 }}</span>
					</template>
					<template v-else>
						<span>{{ profile[key] || field.placeholder }}</span>
					</template>
					<button class="edit-btn" @click="startEditing(key)">
						<i class="fas fa-pencil-alt"></i>
					</button>
				</div>
				<div class="info-edit" v-else>
					<input v-if="field.type === 'text'" :id="key" v-model="profile[key]"
						:placeholder="field.placeholder" />
					<textarea v-if="field.type === 'textarea'" :id="key" v-model="profile[key]"
						:placeholder="field.placeholder"></textarea>
					<select v-if="field.type === 'select'" :id="key" v-model="profile[key]">
						<option v-for="option in field.options" :key="option.value" :value="option.value">
							{{ option.label }}
						</option>
					</select>
					<input v-if="field.type === 'date'" :id="key" v-model="profile[key]" type="date" />
					<input v-if="field.type === 'file'" :id="key" type="file" @change="handleFileUpload"
						accept="image/*" />
					<div class="edit-actions">
						<button class="save-btn" @click="saveField(key)">Сохранить</button>
						<button class="cancel-btn" @click="cancelEditing(key)">Отмена</button>
					</div>
				</div>
			</div>
		</div>

		<!-- Дополнительная информация о пользователе -->
		<h2>Дополнительная информация</h2>
		<div class="additional-info">
			<p><strong>Последний вход:</strong> {{ formatDate(profile.last_online) }}</p>
			<p><strong>Статус верификации:</strong> {{ profile.is_verified ? 'Подтвержден' : 'Не подтвержден' }}</p>
		</div>

		<h2>Наказания пользователя</h2>
		<div class="table-container">
			<table class="penalties-table" v-if="penalties.length">
				<thead>
					<tr>
						<th>Тип</th>
						<th>Причина</th>
						<th>Кем выдано</th>
						<th>Дата назначения</th>
						<th>Дата окончания</th>
						<th>Действия</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(penalty, index) in penalties" :key="index">
						<td>{{ penalty.type }}</td>
						<td>{{ penalty.reason }}</td>
						<td>
							<router-link :to="`/profile/${penalty.issuer_uid}`">
								{{ penalty.issuer.username }}
							</router-link>
						</td>
						<td>{{ formatDate(penalty.issued_at) }}</td>
						<td>{{ formatDate(penalty.expires_at) }}</td>
						<td class="actions">
							<!-- <button @click="editPenaltyModal(penalty.id, penalty.reason)">Редактировать</button> -->
							<button @click="deletePenalty(penalty.id)">Удалить</button>
						</td>
					</tr>
				</tbody>
			</table>
			<p v-else>У пользователя нет наказаний.</p>
		</div>

		<!-- Список комнат -->
		<h2>Комнаты пользователя</h2>
		<div class="table-container">
			<table class="rooms-table" v-if="userRooms.length">
				<thead>
					<tr>
						<th>Название</th>
						<th>Описание</th>
						<th>Регион</th>
						<th>Страна</th>
						<th>Теги</th>
						<th>Дата создания</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(room, index) in userRooms" :key="index">
						<td>{{ room.name }}</td>
						<td>{{ room.description || "Нет описания" }}</td>
						<td>{{ room.region || "Не указан" }}</td>
						<td>{{ room.country || "Не указана" }}</td>
						<td>{{ room.tags || "Нет тегов" }}</td>
						<td>{{ formatDate(room.created_at) }}</td>
					</tr>
				</tbody>
			</table>
			<p v-else>У пользователя нет созданных комнат.</p>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { processFile } from "@/utils/fileUtils";
import UsersServices from "@/API/UsersService";
import ProfileService from "@/API/Admin/ProfileService"

const route = useRoute();
const currentUserRole = ref('admin'); // Здесь должно быть реальное значение роли текущего пользователя

const penalties = ref([]);
const newAvatar = ref(null);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

// Состояния
const profile = ref({
	username: "",
	email: "",
	phone: "",
	status: "active",
	role: "user",
	bio: "",
	country: "",
	city: "",
	avatar: "",
	date_of_birth: null,
	career: null,
	gender: null,
	rating: 0,
	last_online: null,
	is_verified: false,
});

const userRooms = ref([]);

// Вычисляемые свойства для ролей
const availableRoles = computed(() => {
	const roles = [
		{ value: "user", label: "Пользователь" },
		{ value: "moderator", label: "Модератор" },
		{ value: "senior_moderator", label: "Старший модератор" },
		{ value: "admin", label: "Администратор" },
		{ value: "superadmin", label: "Суперадминистратор" },
	];

	// Фильтрация ролей в зависимости от прав текущего пользователя
	if (currentUserRole.value === 'moderator') {
		return roles.filter(r => r.value === 'user');
	} else if (currentUserRole.value === 'admin') {
		return roles.filter(r => ['user', 'moderator', 'senior_moderator'].includes(r.value));
	} else if (currentUserRole.value === 'superadmin') {
		return roles;
	}
	return roles.filter(r => r.value === 'user');
});

// Поля для редактирования
const editableFields = ref({
	username: { label: "Имя пользователя", type: "text", placeholder: "Введите имя пользователя", editing: false },
	email: { label: "Email", type: "text", placeholder: "Введите email", editing: false },
	phone: { label: "Телефон", type: "text", placeholder: "Введите телефон", editing: false },
	status: {
		label: "Статус",
		type: "select",
		options: [
			{ value: "active", label: "Активен" },
			{ value: "inactive", label: "Неактивен" },
			{ value: "deleted", label: "Удален" },
		],
		editing: false,
	},
	role: {
		label: "Роль",
		type: "select",
		options: availableRoles,
		editing: false,
	},
	bio: { label: "Биография", type: "textarea", placeholder: "Введите биографию", editing: false },
	country: { label: "Страна", type: "text", placeholder: "Введите страну", editing: false },
	city: { label: "Город", type: "text", placeholder: "Введите город", editing: false },
	avatar: { label: "Аватар", type: "file", editing: false },
	date_of_birth: { label: "Дата рождения", type: "date", editing: false },
	career: { label: "Профессия", type: "text", placeholder: "Введите профессию", editing: false },
	gender: {
		label: "Пол",
		type: "select",
		options: [
			{ value: "male", label: "Мужской" },
			{ value: "female", label: "Женский" },
			{ value: "other", label: "Другой" },
		],
		editing: false,
	},
	rating: { label: "Рейтинг", type: "text", placeholder: "Введите значение рейтинга", editing: false },
});

const formatDate = (utcDateString) => {
	if (!utcDateString) return '';

	try {
		// Нормализуем строку даты (добавляем 'Z' если нужно)
		const normalizedDate = utcDateString.endsWith('Z') ? utcDateString : `${utcDateString}Z`;
		const date = new Date(normalizedDate);

		if (isNaN(date.getTime())) {
			console.warn('Invalid date format:', utcDateString);
			return '';
		}

		// Форматируем с русской локалью и нужными опциями
		const options = {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		};

		return date.toLocaleString('ru-RU', options);
	} catch (e) {
		console.error('Date formatting error:', e);
		return '';
	}
};

const handleFileUpload = async (event) => {
	const file = event.target.files[0];
	if (!file) return;

	try {
		// Обрабатываем файл с настройками по умолчанию
		const { base64, meta } = await processFile(file, {
			maxWidth: 800,
			quality: 0.8
		});

		// Сохраняем base64 в profile.value.avatar
		profile.value.avatar = {
			url: `data:${meta.type};base64,${base64}`, // Base64-строка с MIME-типом
			type: meta.type, // MIME-тип файла
			name: meta.name, // Имя файла
			size: meta.size, // Размер файла в байтах
		};
	} catch (error) {
		console.error('Ошибка обработки файла:', error);
		alert('Не удалось обработать файл');
	}
};

/* const editPenalty = async (penaltyId, newReason) => {
	try {
		await UsersServices.updatePenalty(penaltyId, { reason: newReason });
		alert("Наказание обновлено");
		// Обновляем список наказаний
		const response = await UsersServices.getUserPenalties(route.params.uid);
		if (response.data.status === "ok") {
			penalties.value = response.data.penalties;
		}
	} catch (error) {
		console.error("Ошибка при редактировании наказания:", error);
	}
}; */

const deletePenalty = async (penaltyId) => {
	if (confirm("Вы уверены, что хотите удалить это наказание?")) {
		try {
			await ProfileService.deletePenalty(penaltyId);
			alert("Наказание удалено");
			// Обновляем список наказаний
			const response = await ProfileService.getUserPenalties(route.params.uid);
			if (response.data.status === "ok") {
				penalties.value = response.data.penalties;
			}
		} catch (error) {
			console.error("Ошибка при удалении наказания:", error);
		}
	}
};

// Начало редактирования поля
const startEditing = (key) => {
	editableFields.value[key].editing = true;
};

// Сохранение изменений в поле
const saveField = async (key) => {
	editableFields.value[key].editing = false;

	// Отправка изменений на сервер
	try {
		await ProfileService.updateAdminProfile(route.params.uid, { [key]: profile.value[key] });
		alert("Изменения сохранены");
	} catch (error) {
		console.error(`Ошибка при сохранении поля ${key}:`, error);
	}
};

// Отмена редактирования
const cancelEditing = (key) => {
	editableFields.value[key].editing = false;
};

onMounted(async () => {
	try {
		// Загрузка данных пользователя
		const response = await UsersServices.get_user_by_uid(route.params.uid);
		if (response.data.status === "ok") {
			profile.value = {
				username: response.data.user.username,
				email: response.data.user.email,
				phone: response.data.user.phone || "",
				status: response.data.user.status || "active",
				role: response.data.user.global_role || "user",
				bio: response.data.user.bio || "",
				country: response.data.user.country || "",
				city: response.data.user.city || "",
				avatar: { url: response.data.user.avatar } || {},
				date_of_birth: response.data.user.date_of_birth || null,
				career: response.data.user.career || null,
				gender: response.data.user.gender || null,
				rating: response.data.user.rating || 0,
				last_online: response.data.user.last_online || null,
				is_verified: response.data.user.is_verified || false,
			};
		}

		// Загрузка комнат пользователя
		const roomsResponse = await ProfileService.getUserRooms(route.params.uid);
		if (roomsResponse.data.status === "ok") {
			userRooms.value = roomsResponse.data.rooms;
		}
	} catch (error) {
		console.error("Ошибка при загрузке данных:", error);
	}

	try {
		const response = await ProfileService.getUserPenalties(route.params.uid);
		if (response.data.status === "ok") {
			penalties.value = response.data.penalties;
		}
	} catch (error) {
		console.error("Ошибка при загрузке наказаний:", error);
	}
});
</script>

<style scoped>
.admin-profile {
	/* max-width: 1200px; */
	margin: 0 auto;
	padding: 20px;
	background: var(--bg-light);
	box-shadow: var(--shadow-light);
	border-radius: 8px;
}

.profile-info {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
	gap: 20px;
	margin-top: 20px;
}

.info-item {
	margin-bottom: 15px;
}

.info-item label {
	display: block;
	font-weight: bold;
	margin-bottom: 5px;
}

.info-display {
	display: flex;
	align-items: center;
	justify-content: space-between;
	min-height: 40px;
}

.info-display span {
	flex-grow: 1;
}

.avatar-preview {
	width: 50px;
	height: 50px;
	border-radius: 50%;
	object-fit: cover;
}

.edit-btn {
	background: none;
	border: none;
	cursor: pointer;
	color: var(--primary-color);
	font-size: 16px;
	margin-left: 10px;
}

.info-edit input,
.info-edit textarea,
.info-edit select {
	width: 100%;
	padding: 8px;
	margin-bottom: 10px;
	border: 1px solid var(--border-color);
	border-radius: 4px;
}

.info-edit .edit-actions {
	display: flex;
	gap: 10px;
}

.save-btn,
.cancel-btn {
	padding: 8px 16px;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}

.save-btn {
	background-color: var(--primary-color);
	color: white;
}

.cancel-btn {
	background-color: var(--danger-color);
	color: white;
}

.additional-info {
	margin-top: 20px;
}

.additional-info p {
	margin-bottom: 5px;
}

.table-container {
	overflow-x: auto;
}

.rooms-table,
.penalties-table {
	width: 100%;
	border-collapse: collapse;
	margin-top: 20px;
}

.rooms-table th,
.rooms-table td,
.penalties-table th,
.penalties-table td {
	border: 1px solid var(--border-color);
	padding: 8px;
	text-align: left;
}

.rooms-table th,
.penalties-table th {
	background-color: var(--bg-light);
}

.actions {
	white-space: nowrap;
}

@media (max-width: 768px) {
	.profile-info {
		grid-template-columns: 1fr;
	}

	.info-edit .edit-actions {
		flex-direction: column;
	}
}
</style>