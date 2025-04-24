<template>
	<aside class="chat-sidebar-right" :class="{ active: isActive }">
		<!-- Кнопка закрытия -->
		<button class="close-sidebar" aria-label="Закрыть сайдбар" @click="closeSidebar">
			<i class="fas fa-arrow-right"></i>
		</button>

		<!-- Вкладки -->
		<div class="sidebar-tabs">
			<button class="tab-button" :class="{ active: activeTab === 'info' }" @click="activeTab = 'info'">
				Информация
			</button>
			<button class="tab-button" :class="{ active: activeTab === 'users' }" @click="activeTab = 'users'">
				Пользователи ({{ users.length }})
			</button>
		</div>

		<!-- Контент вкладки "Информация" -->
		<div v-show="activeTab === 'info'" class="chat-sidebar-info">
			<div v-if="!isEditing">
				<h3 style="text-align: center; margin-bottom: 10px;">{{ roomInfo.name }}</h3>
				<p><strong>Описание:</strong> {{ roomInfo.description || 'Нет описания' }}</p>
				<p><strong>Страна:</strong> {{ roomInfo.country }}</p>
				<p><strong>Регион:</strong> {{ roomInfo.region }}</p>
				<p><strong>Теги:</strong> {{ roomInfo.tags }}</p>
				<p><strong>Дата создания:</strong> {{ formatDate(roomInfo.created_at) }}</p>
				<p><strong>Владелец:</strong>
					<router-link class="sidebar-link" v-if="owner" :to="`/profile/${owner.uid}`">{{ owner.username
					}}</router-link>
					<span v-else>Неизвестно</span>
				</p>
				<div class="rating-visualization">
					<h4>Рейтинг комнаты: {{ roomInfo.rating }}</h4>
					<div v-if="roomInfo.rating > 0">
						<EnergyGrid :rating="roomInfo.rating" />
					</div>
					<p v-else>У комнаты пока нет рейтинга.</p>
				</div>

				<!-- Кнопки управления для владельца -->
				<div v-if="isOwner" class="room-actions">
					<button @click="startEditing" class="action-button edit-button">
						<i class="fas fa-edit"></i> Редактировать
					</button>
				</div>
			</div>

			<!-- Форма редактирования -->
			<div v-else class="edit-form">
				<h3 style="text-align: center; margin-bottom: 10px;">Редактирование комнаты</h3>
				<form @submit.prevent="saveChanges">
					<div class="form-group">
						<label>Название:</label>
						<input v-model="editForm.name" type="text" class="form-input">
					</div>
					<div class="form-group">
						<label>Описание:</label>
						<textarea v-model="editForm.description" class="form-textarea"></textarea>
					</div>
					<div class="form-group">
						<label>Теги (через запятую):</label>
						<input v-model="editForm.tags" type="text" class="form-input">
					</div>
					<div class="form-actions">
						<button type="button" @click="cancelEditing" class="action-button cancel-button">
							Отмена
						</button>
						<button type="submit" class="action-button save-button">
							Сохранить
						</button>
					</div>
				</form>
			</div>
		</div>

		<!-- Контент вкладки "Пользователи" -->
		<div v-show="activeTab === 'users'" class="chat-sidebar-users">
			<div class="chat-sidebar-users-list" v-if="users.length > 0">
				<div v-for="user in users" :key="user.uid" class="user-item-wrapper">
					<router-link :to="`/profile/${user.uid}`" class="username">
						<div class="chat-sidebar-users-item" :data-user-id="user.uid">
							<img :src="apiBaseUrl + user.avatar" alt="Avatar" class="user-avatar">
							<span>{{ user.username }}</span>
							<span v-if="user.uid === roomInfo.owner_uid" class="user-badge owner">Владелец</span>
							<span v-else-if="isModerator(user.uid)" class="user-badge moderator">Модератор</span>
						</div>
					</router-link>

					<!-- Меню действий для владельца/модератора -->
					<div v-if="(isOwner || isCurrentUserModerator) && user.uid !== currentUserUid && user.uid !== roomInfo.owner_uid"
						class="user-actions">
						<button @click.stop="toggleUserMenu(user.uid)" class="user-menu-button">
							<i class="fas fa-ellipsis-v"></i>
						</button>

						<div v-if="activeUserMenu === user.uid" class="user-menu-dropdown">
							<button v-if="isOwner" @click.stop="toggleModeratorStatus(user.uid)" class="menu-item">
								{{ isModerator(user.uid) ? 'Убрать модератора' : 'Назначить модератором' }}
							</button>
							<button @click.stop="banUser(user.uid)" class="menu-item ban-item">
								<i class="fas fa-ban"></i> Заблокировать
							</button>
						</div>
					</div>
				</div>
			</div>
			<p v-else>Нет подключенных пользователей</p>
		</div>
	</aside>
</template>

<script setup>
import { defineProps, defineEmits, ref, onMounted, computed } from 'vue';
import EnergyGrid from '@/components/EnergyGrid/index.vue';
import UsersServices from '@/API/UsersService';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';

const store = useStore();
const router = useRouter();

const props = defineProps({
	isActive: {
		type: Boolean,
		default: false,
	},
	roomInfo: {
		type: Object,
		default: () => ({}),
	},
	users: {
		type: Array,
		default: () => [],
	},
});

const emit = defineEmits(['close', 'update-room', 'user-banned', 'moderator-changed']);

const owner = ref(null);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const activeTab = ref('info');
const isEditing = ref(false);
const activeUserMenu = ref(null);
const editForm = ref({
	name: '',
	description: '',
	tags: ''
});

const currentUserUid = computed(() => store.getters['getUser']?.uid);
const isOwner = computed(() => currentUserUid.value === props.roomInfo.owner_uid);
const isCurrentUserModerator = computed(() => isModerator(currentUserUid.value));

const isModerator = (uid) => {
	return props.roomInfo.moderators?.includes(uid) || false;
};

const toggleUserMenu = (userId) => {
	activeUserMenu.value = activeUserMenu.value === userId ? null : userId;
};

const toggleModeratorStatus = async (userId) => {
	try {
		const action = isModerator(userId) ? 'remove_moderator' : 'add_moderator';

		/* await sendSocketMessage({
			type: 'moderator_action',
			room_uid: props.roomInfo.uid,
			target_user_uid: userId,
			action: action
		}); */

		emit('moderator-changed', { userId, isModerator: action === 'add_moderator' });
		activeUserMenu.value = null;

	} catch (error) {
		console.error('Ошибка при изменении статуса модератора:', error);
	}
};

const banUser = async (userId) => {
	try {
		/* await sendSocketMessage({
			type: 'ban_user',
			room_uid: props.roomInfo.uid,
			target_user_uid: userId,
			reason: 'Нарушение правил чата'
		}); */

		emit('user-banned', userId);
		activeUserMenu.value = null;

	} catch (error) {
		console.error('Ошибка при блокировке пользователя:', error);
	}
};

const startEditing = () => {
	editForm.value = {
		name: props.roomInfo.name,
		description: props.roomInfo.description,
		tags: props.roomInfo.tags
	};
	isEditing.value = true;
};

const cancelEditing = () => {
	isEditing.value = false;
};

const saveChanges = () => {
	emit('update-room', editForm.value);
	isEditing.value = false;
};

const closeSidebar = () => {
	emit('close');
};

const formatDate = (dateString) => {
	const date = new Date(dateString);
	return date.toLocaleDateString();
};

onMounted(async () => {
	if (props.roomInfo.owner_uid) {
		try {
			const response = await UsersServices.get_user_by_uid(props.roomInfo.owner_uid);
			if (response.data.status === 'ok') {
				owner.value = response.data.user;
			}
		} catch (error) {
			console.error('Ошибка при получении данных владельца:', error);
		}
	}
});
</script>

<style scoped>
.chat-sidebar-right {
	position: relative;
	height: 100%;
	min-width: 300px;
	width: 300px;
	display: flex;
	flex-direction: column;
	padding: 10px;
	background-color: var(--sidebar-bg-light);
	transition: transform 0.3s ease-in-out, opacity 0.3s ease-in-out;
}

@media screen and (max-width: 991px) {
	.chat-sidebar-right {
		position: fixed;
		right: 0;
		transform: translateX(120%);
	}

	.chat-sidebar-right.active {
		transform: translateX(0%);
	}
}

@media screen and (max-width: 991px) {
	.chat-sidebar-right {
		height: calc(100% - (50px + 8px));
	}
}

.close-sidebar {
	cursor: pointer;
	position: absolute;
	top: 15px;
	left: -18px;
	background: none;
	border: none;
	display: none;
	background-color: #ccc;
	border-radius: 100%;
	padding: 5px;
	width: 30px;
	height: 30px;
}

@media screen and (max-width: 991px) {
	.close-sidebar {
		display: block;
	}
}

/* Стили для вкладок */
.sidebar-tabs {
	display: flex;
	border-bottom: 1px solid #ddd;
	margin-bottom: 15px;
}

.tab-button {
	flex: 1;
	padding: 10px;
	background: none;
	border: none;
	cursor: pointer;
	border-bottom: 2px solid transparent;
	transition: all 0.3s;
	color: var(--text-light);
}

.tab-button.active {
	border-bottom: 2px solid var(--primary-color);
	font-weight: bold;
}

.tab-button:hover {
	background-color: rgba(0, 0, 0, 0.05);
}

.chat-sidebar-info {
	padding: 10px;
	flex: 1;
	overflow-y: auto;
}

.sidebar-link {
	text-decoration: none;
	color: var(--text-light);
	margin-left: 5px;
	transition: text-decoration .15s ease-in;
}

.sidebar-link:hover {
	text-decoration: underline;
}

.chat-sidebar-users {
	padding: 10px;
	flex: 1;
	overflow-y: auto;
}

.user-item-wrapper {
	position: relative;
	display: flex;
	align-items: center;
	margin-bottom: 5px;
	border-radius: 8px;
	transition: background-color .15s ease-in;
}

.user-item-wrapper:hover {
	background-color: rgba(0, 123, 255, 0.1);
}

.chat-sidebar-users-list {
	display: flex;
	flex-direction: column;
	gap: 5px;
}

.chat-sidebar-users-item {
	display: flex;
	align-items: center;
	color: var(--text-light);
	padding: 8px;
	flex-grow: 1;
}

.user-avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	margin-right: 10px;
}

.user-badge {
	font-size: 0.8em;
	padding: 2px 6px;
	border-radius: 4px;
	margin-left: 8px;
}

.user-badge.owner {
	background-color: #ffc107;
	color: #000;
}

.user-badge.moderator {
	background-color: #17a2b8;
	color: #fff;
}

.user-actions {
	position: relative;
	margin-left: auto;
}

.user-menu-button {
	background: none;
	border: none;
	cursor: pointer;
	padding: 8px;
	color: var(--text-light);
}

.user-menu-dropdown {
	position: absolute;
	right: 0;
	top: 100%;
	background-color: white;
	border-radius: 4px;
	box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
	z-index: 10;
	min-width: 180px;
}

.menu-item {
	display: block;
	width: 100%;
	padding: 8px 12px;
	text-align: left;
	background: none;
	border: none;
	cursor: pointer;
	transition: background-color 0.2s;
}

.menu-item:hover {
	background-color: #f5f5f5;
}

.menu-item.ban-item {
	color: #dc3545;
}

/* Стили для формы редактирования */
.edit-form {
	padding: 10px;
}

.form-group {
	margin-bottom: 15px;
}

.form-group label {
	display: block;
	margin-bottom: 5px;
	font-weight: bold;
}

.form-input,
.form-textarea {
	width: 100%;
	padding: 8px;
	border: 1px solid #ddd;
	border-radius: 4px;
}

.form-textarea {
	min-height: 80px;
	resize: vertical;
}

.form-actions {
	display: flex;
	justify-content: flex-end;
	gap: 10px;
	margin-top: 15px;
}

.action-button {
	padding: 8px 15px;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: background-color 0.2s;
}

.edit-button {
	background-color: #17a2b8;
	color: white;
}

.edit-button:hover {
	background-color: #138496;
}

.save-button {
	background-color: #28a745;
	color: white;
}

.save-button:hover {
	background-color: #218838;
}

.cancel-button {
	background-color: #6c757d;
	color: white;
}

.cancel-button:hover {
	background-color: #5a6268;
}

.room-actions {
	margin-top: 15px;
	padding-top: 15px;
	border-top: 1px solid #eee;
}

.rating-visualization {
	margin-top: 10px;
	padding-top: 10px;
	border-top: 1px solid #eee;
}
</style>