<template>
	<div class="user-profile">
		<transition name="fade" v-if="isLoading">
			<Loader :message="'Загрузка профиля...'" />
		</transition>

		<div v-else-if="errorMessage" class="error-message"> <!-- Отображение ошибки -->
			<p>{{ errorMessage }}</p>
		</div>

		<div v-else-if="user">
			<!-- Шапка профиля -->
			<div class="profile-header">
				<div class="profile-avatar-container">
					<img :src="user.avatar" alt="Аватар пользователя" class="profile-avatar" />
				</div>
				<div class="profile-info">
					<h1 class="profile-name">{{ user.username }}</h1>
					<p class="profile-email">{{ user.email }}</p>
				</div>
				<!-- Кнопка редактирования (только для текущего пользователя) -->
				<button v-if="canEditProfile" @click="toggleEditForm" class="edit-profile-btn">Редактировать профиль</button>
			</div>

			<!-- Основное содержимое профиля -->
			<div class="profile-details">
				<div class="profile-detail-item">
					<span class="profile-detail-label">Рейтинг:</span>
					<Rating :rating="user.rating" />
				</div>
				<div class="profile-detail-item">
					<span class="profile-detail-label">Страна:</span>
					<span class="profile-detail-value">{{ user.country || 'Не указана' }}</span>
				</div>
				<div class="profile-detail-item">
					<span class="profile-detail-label">Город:</span>
					<span class="profile-detail-value">{{ user.city || 'Не указан' }}</span>
				</div>
				<div class="profile-detail-item">
					<span class="profile-detail-label">Биография:</span>
					<span class="profile-detail-value">{{ user.bio || 'Нет информации' }}</span>
				</div>
			</div>
			<EditProfileForm v-if="isEditing" :user="user" @close="toggleEditForm" />
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, computed, watchEffect } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useStore } from 'vuex';
import UsersServices from '@/API/UsersService';

import Loader from '@/components/Loader/index.vue'
import Rating from "@/components/Rating/Rating.vue";
import EditProfileForm from '@/components/EditProfileForm/index.vue';

const route = useRoute();
const router = useRouter();
const store = useStore();

// Состояние для хранения данных пользователя
const user = ref(null);
const isLoading = ref(true); // Флаг загрузки
const errorMessage = ref(''); // Сообщение об ошибке
const isEditing = ref(false);

// Получаем текущего пользователя из Vuex store
const currentUser = computed(() => store.getters.getUser);

// Проверка, является ли текущий пользователь владельцем профиля
const isCurrentUser = computed(() => {
	const profileUid = route.params.uid;
	return !profileUid || profileUid === currentUser.value?.uid;
});

// Проверка прав на редактирование профиля
const canEditProfile = computed(() => {
	if (isCurrentUser.value) {
		return true; // Текущий пользователь всегда может редактировать свой профиль
	}

	const userRole = currentUser.value?.global_role;
	return ['admin', 'moderator', 'superadministrator'].includes(userRole); // Модераторы и администраторы могут редактировать чужие профили
});

// Функция для загрузки данных пользователя
const loadUserData = async (uid) => {
	try {
		const response = await UsersServices.get_user_by_uid(uid);
		if (response.data.status === 'ok') {
			user.value = response.data.user;

			// Обновляем заголовок страницы
			document.title = `Профиль: ${response.data.user.username}`;
		} else {
			errorMessage.value = `Ошибка: ${response.data.message}`;
		}
	} catch (error) {
		errorMessage.value = 'Ошибка при загрузке профиля пользователя.';
		console.error('Ошибка при загрузке профиля:', error);
	} finally {
		isLoading.value = false; // Загрузка завершена
	}
};

// Логика для открытия/закрытия формы редактирования
const toggleEditForm = () => {
	isEditing.value = !isEditing.value;
};

onMounted(async () => {
	const profileUid = route.params.uid;

	// Если параметр uid отсутствует, используем UID текущего пользователя
	if (!profileUid) {
		const currentUid = currentUser.value?.uid;
		if (currentUid) {
			router.replace({ path: `/profile/${currentUid}` });
		} else {
			errorMessage.value = 'UID текущего пользователя не определён.';
			isLoading.value = false;
		}
		return;
	}

	// Загружаем данные пользователя
	await loadUserData(profileUid);
});

// Наблюдаем за изменениями параметра uid
watchEffect(() => {
	const profileUid = route.params.uid;
	if (profileUid) {
		loadUserData(profileUid);
	}
});
</script>

<style scoped>
/* Специфичные стили для профиля */
.user-profile {
	max-width: 960px;
	margin: 0 auto;
	padding: 20px;
	background: var(--bg-light);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	border-radius: 8px;
}

.profile-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 20px;
}

.profile-avatar-container {
	position: relative;
}

.profile-avatar {
	width: 120px;
	height: 120px;
	border-radius: 50%;
	overflow: hidden;
	border: 4px solid var(--profile-avatar-border);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.profile-info {
	margin-left: 20px;
}

.profile-name {
	font-size: 24px;
	font-weight: bold;
}

.profile-email {
	color: var(--profile-details-color);
}

.edit-profile-btn {
	background: var(--profile-edit-btn);
	color: white;
	border: none;
	padding: 8px 16px;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
}

.edit-profile-btn:hover {
	background: var(--profile-edit-btn-hover);
}

.profile-details {
	margin-top: 20px;
}

.profile-detail-item {
	margin-bottom: 10px;
}

.profile-detail-label {
	font-weight: bold;
}

.profile-detail-value {
	color: var(--profile-details-color);
}

.error-message {
	color: red;
	margin-top: 10px;
}

.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>