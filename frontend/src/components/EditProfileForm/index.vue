<template>
	<div class="edit-profile-form">
		<h2>Редактирование профиля</h2>
		<form @submit.prevent="saveProfile">
			<!-- Форма редактирования -->
			<div class="form-group">
				<label for="first_name">Имя:</label>
				<input type="text" id="first_name" v-model="profile.first_name" />
			</div>
			<div class="form-group">
				<label for="last_name">Фамилия:</label>
				<input type="text" id="last_name" v-model="profile.last_name" />
			</div>
			<div class="form-group">
				<label for="email">Email:</label>
				<input type="email" id="email" v-model="profile.email" required />
			</div>
			<div class="form-group">
				<label for="phone">Телефон:</label>
				<input type="text" id="phone" v-model="profile.phone" />
			</div>
			<div class="form-group">
				<label for="country">Страна:</label>
				<select id="country" v-model="selectedCountry" @change="filterCities">
					<option value="">Выберите страну</option>
					<option v-for="country in countries" :key="country" :value="country">{{ country }}</option>
				</select>
			</div>
			<div class="form-group">
				<label for="city">Город:</label>
				<input type="text" id="city" v-model="cityInput" list="city-list" />
				<datalist id="city-list">
					<option v-for="city in filteredCities" :key="city" :value="city">{{ city }}</option>
				</datalist>
			</div>
			<div class="form-group">
				<label for="bio">Биография:</label>
				<textarea id="bio" v-model="profile.bio"></textarea>
			</div>

			<!-- Кнопка удаления профиля -->
			<button v-if="canDeleteProfile" @click="openDeleteModal" class="delete-profile-btn">Удалить профиль</button>

			<div class="form-actions">
				<button type="submit">Сохранить изменения</button>
				<button type="button" @click="cancelEdit">Отмена</button>
			</div>
		</form>

		<!-- Модальное окно удаления -->
		<DeleteUserModal ref="deleteModal" />
	</div>
</template>

<script setup>
import { ref, computed, defineEmits, defineProps } from 'vue';
import DeleteUserModal from '@/components/DeleteUserModal/index.vue';
import { useRoute } from 'vue-router';
import { useStore } from 'vuex';

const route = useRoute();
const store = useStore();

// Пропсы
const props = defineProps({
	user: {
		type: Object,
		required: true,
	},
});

// Эмиты
const emit = defineEmits(['update', 'close']);

const currentUser = computed(() => store.getters.getUser);

const isCurrentUser = computed(() => {
	const profileUid = route.params.uid;
	return !profileUid || profileUid === currentUser.value?.uid;
});

// Состояние формы
const profile = ref({ ...props.user });
const selectedCountry = ref(props.user.country || '');
const cityInput = ref(props.user.city || '');
const countries = ['Россия', 'США', 'Канада']; // Пример списка стран
const cities = {
	Россия: ['Москва', 'Санкт-Петербург', 'Новосибирск'],
	США: ['Нью-Йорк', 'Лос-Анджелес', 'Чикаго'],
	Канада: ['Торонто', 'Ванкувер', 'Монреаль'],
};

// Проверка прав на удаление профиля
const canDeleteProfile = computed(() => {
	return isCurrentUser.value; // Только текущий пользователь может удалять свой профиль
});

// Фильтрация городов
const filteredCities = computed(() => {
	return selectedCountry.value ? cities[selectedCountry.value] || [] : [];
});

// Сохранение изменений
const saveProfile = async () => {
	try {
		// Проверка email и телефона на уникальность
		const isEmailUnique = await checkEmailUniqueness(profile.value.email);
		const isPhoneUnique = await checkPhoneUniqueness(profile.value.phone);

		if (!isEmailUnique) {
			alert('Этот email уже используется.');
			return;
		}
		if (!isPhoneUnique) {
			alert('Этот телефон уже используется.');
			return;
		}

		// Обновляем данные профиля
		profile.value.city = cityInput.value;
		profile.value.country = selectedCountry.value;

		emit('update', profile.value);
		emit('close');
	} catch (error) {
		console.error('Ошибка при обновлении профиля:', error);
	}
};

// Отмена редактирования
const cancelEdit = () => {
	emit('close');
};

// Открытие модального окна удаления
const deleteModal = ref(null);
const openDeleteModal = () => {
	deleteModal.value.openDeleteModal();
};

// Проверка уникальности email
const checkEmailUniqueness = async (email) => {
	// Замените на реальный запрос к API
	return !['existing@example.com'].includes(email);
};

// Проверка уникальности телефона
const checkPhoneUniqueness = async (phone) => {
	// Замените на реальный запрос к API
	return !['+79001234567'].includes(phone);
};
</script>

<style scoped>
.edit-profile-form {
	max-width: 600px;
	margin: 20px auto;
	padding: 20px;
	background: var(--bg-light);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	border-radius: 8px;
}

.form-group {
	margin-bottom: 15px;
}

label {
	display: block;
	font-weight: bold;
	margin-bottom: 5px;
}

input,
select,
textarea {
	width: 100%;
	padding: 8px;
	border: 1px solid #ccc;
	border-radius: 4px;
}

button {
	padding: 8px 16px;
	background: var(--profile-edit-btn);
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
	margin-right: 10px;
}

button:hover {
	background: var(--profile-edit-btn-hover);
}

.delete-profile-btn {
	background: red;
	color: white;
	border: none;
	padding: 8px 16px;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
	margin-top: 10px;
}

.delete-profile-btn:hover {
	background: darkred;
}
</style>