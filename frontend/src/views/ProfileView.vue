<template>
	<AvatarUploadModal v-if="isAvatarUploadModalOpen" @close="toggleAvatarUploadModal" @upload="handleSuccessfulUpdate"
		:is-modal-open="isAvatarUploadModalOpen" :user_uid="route.params.uid" />
	<EditProfileForm :modalShow="isEditProfileModalOpen" :user="profileData || {}" @close="toggleEditProfileModal"
		@save="handleProfileUpdate" />
	<ProfileModalForAdmin :show-modal="isModerationModalOpen" :user-uid="route.params.uid"
		@close="toggleModerationModal" />
	<div class="user-profile">
		<transition name="fade" v-if="isLoading">
			<Loader :message="'Загрузка профиля...'" />
		</transition>

		<div v-else-if="errorMessage" class="error-message"> <!-- Отображение ошибки -->
			<p>{{ errorMessage }}</p>
		</div>

		<div v-else-if="profileData">
			<!-- Шапка профиля -->
			<div class="profile-header">
				<div class="profile-avatar-container" @click="canEditProfile && toggleAvatarUploadModal()">
					<img :src="apiBaseUrl + profileData.avatar || '/images/default-avatar.png'"
						alt="Аватар пользователя" class="profile-avatar" />
				</div>

				<div class="profile-info">
					<h1 class="profile-name">
						{{ profileData.first_name || profileData.last_name ? `${profileData.first_name}
						${profileData.last_name} (${profileData.username})` : profileData.username }}
					</h1>
					<p class="profile-email">{{ profileData.email }}</p>
					<p v-if="profileData.global_role != 'user'" class="profile-email">{{ profileData.global_role }}</p>
				</div>
				<UserStatus v-if="!isCurrentUser" :userId="route.params.uid" />
				<div class="profile-actions">
					<button v-if="!isCurrentUser && isModeratorOrAdmin" @click="openAdminPanel" class="admin-panel-btn">
						Открыть в админпанели
					</button>
					<button v-if="canEditProfile" @click="toggleEditProfileModal" class="edit-profile-btn">Редактировать
						профиль</button>
					<button v-if="!isCurrentUser" @click="openChatWithUser" class="message-button">Отправить
						сообщение</button>
				</div>
				<div class="moderation-actions" v-if="isModeratorOrAdmin && route.params.uid != currentUser.uid">
					<button @click="toggleModerationModal">Назначить наказание</button>
				</div>
			</div>

			<!-- Основное содержимое профиля -->
			<div class="profile-details">
				<div class="profile-detail-item">
					<span class="profile-detail-label">Рейтинг:</span>
					<Rating :rating="profileData.rating" />
				</div>
				<div class="profile-detail-item">
					<span class="profile-detail-label">Страна:</span>
					<span class="profile-detail-value">{{ profileData.country || 'Не указана' }}</span>
				</div>
				<div class="profile-detail-item">
					<span class="profile-detail-label">Город:</span>
					<span class="profile-detail-value">{{ profileData.city || 'Не указан' }}</span>
				</div>
				<div class="profile-detail-item">
					<span class="profile-detail-label">Биография:</span>
					<span class="profile-detail-value">{{ profileData.bio || 'Нет информации' }}</span>
				</div>
			</div>
		</div>
	</div>
	<div class="profile-posts" v-if="false">
		<h2>Личные записи</h2>
		<p>Функционал временно недоступен.</p>
	</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watchEffect, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useStore } from 'vuex';

import UsersServices from '@/API/UsersService';
import CSRFService from '@/API/CSRFService';

import Loader from '@/components/Loader/index.vue'
import Rating from "@/components/Rating/Rating.vue";
import UserStatus from "@/components/UserStatus/index.vue"
import EditProfileForm from '@/components/EditProfileForm/Modals/EditProfileModal.vue';
import AvatarUploadModal from '@/components/EditProfileForm/Modals/AvatarUploadModal.vue';
import ProfileModalForAdmin from '@/components/AdminComponents/Modals/ProfileModalForAdmin.vue';

const emits = defineEmits(['update'])

const route = useRoute();
const router = useRouter();
const store = useStore();

// Состояние для хранения данных пользователя
const profileData = ref(null);
const isLoading = ref(true); // Флаг загрузки
const errorMessage = ref(''); // Сообщение об ошибке
const isAvatarUploadModalOpen = ref(false);
const isEditProfileModalOpen = ref(false);
const isModerationModalOpen = ref(false);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

// Получаем текущего пользователя из Vuex store
const currentUser = computed(() => store.getters.getUser);

// Проверка, является ли текущий пользователь владельцем профиля
const isCurrentUser = computed(() => {
	const profileUid = route.params.uid;
	return !profileUid || profileUid === currentUser.value?.uid;
});

const isModeratorOrAdmin = computed(() => {
	return ['admin', 'moderator', 'superadmin'].includes(currentUser.value?.global_role);
});

// Проверка прав на редактирование профиля
const canEditProfile = computed(() => {
	if (isCurrentUser.value) {
		return true; // Текущий пользователь всегда может редактировать свой профиль
	}

	const userRole = currentUser.value?.global_role;
	return ['admin', 'moderator', 'superadmin'].includes(userRole); // Модераторы и администраторы могут редактировать чужие профили
});

const openChatWithUser = () => {
	store.dispatch('messenger/setActiveDialog', route.params.uid);
	router.push('/messenger');
};

// Функция для загрузки данных пользователя
const loadUserData = async (uid) => {
	profileData.value = null; // Очистка данных пользователя
	errorMessage.value = ''; // Очистка ошибок
	isLoading.value = true; // Включение индикатора загрузки

	try {
		const response = await UsersServices.get_user_by_uid(uid);
		if (response.data.status === 'ok') {
			profileData.value = response.data.user; // Сохраняем данные пользователя
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

// Логика для открытия/закрытия формы редактирования аватара
const toggleAvatarUploadModal = () => {
	if (!canEditProfile.value) return;
	isAvatarUploadModalOpen.value = !isAvatarUploadModalOpen.value;
};

// Логика для открытия/закрытия формы редактирования профиля
const toggleEditProfileModal = async () => {
	if (!profileData.value) {
		await loadUserData(route.params.uid || currentUser.value?.uid);
	}
	isEditProfileModalOpen.value = !isEditProfileModalOpen.value;
};

const toggleModerationModal = () => {
	isModerationModalOpen.value = !isModerationModalOpen.value;
};

const handleProfileUpdate = async (updatedData) => {
	isEditProfileModalOpen.value = false;

	try {
		await prepareCSRF();
		const response = await sendProfileUpdateRequest(updatedData);

		if (response.data.status === 'ok') {
			handleSuccessfulUpdate(response.data);
		} else {
			handleUpdateError(response.data.message);
		}
	} catch (error) {
		console.error('Ошибка при обновлении профиля:', error);
	}
};

// Подготовка CSRF-токена
const prepareCSRF = async () => {
	await CSRFService.getCSRF();
};

// Отправка данных на сервер
const sendProfileUpdateRequest = async (updatedData) => {
	console.log('Отправляем данные для обновления:', updatedData);
	return await UsersServices.updateProfile(profileData.value.uid, updatedData);
};

// Обработка успешного обновления
const handleSuccessfulUpdate = (responseData) => {
	//console.log('Профиль успешно обновлен:', responseData);
	emits('close'); // Закрываем модалку

	// Если редактируется собственный профиль, обновляем данные в Vuex
	if (route.params.uid === currentUser.value.uid) {
		store.commit('setUser', responseData.user);
	}

	// Перезагружаем данные пользователя
	loadUserData(route.params.uid || currentUser.value?.uid);
};

// Обработка ошибки обновления
const handleUpdateError = (errorMessage) => {
	console.error('Ошибка при обновлении профиля:', errorMessage);
};

const openAdminPanel = () => {
	router.push(`/admin/profile/${route.params.uid}`);
};

onMounted(async () => {
	const profileUid = route.params.uid || currentUser.value?.uid;

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

watchEffect(() => {
	const profileUid = route.params.uid;
	if (profileUid) {
		loadUserData(profileUid);
	}
});
watch(() => route.params.uid, (newUid) => {
	if (newUid) {
		store.dispatch('messenger/subscribeToStatuses', [newUid]);
	}
}, { immediate: true });

// Отписываемся при размонтировании
onUnmounted(() => {
	const profileUid = route.params.uid;
	if (profileUid) {
		store.dispatch('messenger/unsubscribeFromStatuses', [profileUid]);
	}
});
</script>

<style scoped>
/* Специфичные стили для профиля */
.user-profile {
	/* max-width: 960px; */
	margin: 0 auto;
	padding: 20px;
	background: var(--bg-light);
	box-shadow: var(--shadow-light);
	border-radius: 8px;
	color: var(--text-light);
}

.profile-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 20px;
	flex-wrap: wrap;
	/* Для адаптации на маленьких экранах */
}

.profile-avatar-container {
	cursor: pointer;
	position: relative;
	width: 120px;
	height: 120px;
	margin-right: 20px;
	flex-shrink: 0;
	/* Предотвращаем сжатие аватара */
}

.profile-avatar {
	width: 100%;
	height: 100%;
	border-radius: 50%;
	overflow: hidden;
	border: 4px solid var(--profile-avatar-border);
	box-shadow: var(--shadow-light);
}

.profile-info {
	flex: 1;
	min-width: 0;
	/* Предотвращаем переполнение текста */
}

.profile-name {
	font-size: 24px;
	font-weight: bold;
	margin-bottom: 5px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.profile-email {
	color: var(--profile-details-color);
	font-size: 0.9em;
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

.message-button {
	background: var(--primary-color);
	color: white;
	border: none;
	padding: 8px 16px;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
	margin-left: 10px;
}

.message-button:hover {
	background: var(--primary-color-hover);
}

.profile-details {
	margin-top: 20px;
}

.profile-detail-item {
	margin-bottom: 10px;
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.profile-detail-label {
	font-weight: bold;
	min-width: 100px;
	/* Фиксированная ширина для выравнивания */
}

.profile-detail-value {
	color: var(--profile-details-color);
	word-break: break-word;
	/* Для длинного текста */
}

.error-message {
	color: red;
	margin-top: 10px;
	text-align: center;
}

.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}

/* Адаптация для мобильных устройств */
@media (max-width: 768px) {
	.profile-header {
		flex-direction: column;
		align-items: flex-start;
	}

	.profile-avatar-container {
		margin-right: 0;
		margin-bottom: 15px;
	}

	.profile-info {
		margin-left: 0;
	}

	.edit-profile-btn,
	.message-button {
		width: 100%;
		margin-top: 10px;
	}
}
</style>