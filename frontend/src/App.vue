<script setup>
import { ref, onMounted } from 'vue';
import HeaderComponent from './components/HeaderComponent/index.vue';
import { useStore } from 'vuex';
import $api from '@/API/index.js';

const store = useStore();
const serverAvailable = ref(true);
const showErrorNotification = ref(false);

// Проверка доступности сервера
const checkServerAvailability = async () => {
	try {
		await $api.get('/health');
	} catch (error) {
		serverAvailable.value = false;
		showErrorNotification.value = true;

		setTimeout(() => {
			showErrorNotification.value = false;
		}, 5000);
	}
};

onMounted(async () => {
	if (localStorage.getItem('access_token')) {
		// Проверяем, есть ли данные пользователя в хранилище
		if (!store.getters.getUser && localStorage.getItem('user')) {
			try {
				// Загружаем данные пользователя с сервера
				//await store.dispatch('fetchUserData');
				store.commit('setUser', JSON.parse(localStorage.getItem('user')));
			} catch (error) {
				console.error('Ошибка загрузки данных пользователя:', error);
				// Если загрузка не удалась, очищаем состояние авторизации
				store.commit('user/clearUser');
				localStorage.removeItem('access_token');
			}
		}
	}
	checkServerAvailability();
});
</script>

<template>
	<div class="container chat-container">
		<HeaderComponent />

		<!-- Всплывающее уведомление об ошибке -->
		<transition name="fade">
			<div v-if="showErrorNotification" class="error-notification">
				<p>Ошибка: сервер недоступен. Пожалуйста, проверьте соединение.</p>
			</div>
		</transition>

		<div class="row mt-1">
			<RouterView />
		</div>
	</div>
</template>

<style scoped>
/* .chat-wrapper {
	padding: 0 10px;
} */
.error-notification {
	background-color: rgba(255, 99, 71, 0.9); /* Светло-красный цвет */
	color: white;
	padding: 15px;
	text-align: center;
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	z-index: 1000; /* Убедитесь, что уведомление поверх других элементов */
}

.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.5s ease, transform 0.5s ease; /* Плавный переход для прозрачности и трансформации */
}

.fade-enter {
	opacity: 0; /* Начальная прозрачность */
	transform: translateY(-20px); /* Смещение вверх */
}

.fade-leave-to {
	opacity: 0; /* Конечная прозрачность */
	transform: translateY(-20px); /* Смещение вверх */
}

/* Добавим немного задержки для fade-leave */
.fade-leave-active {
	transition: opacity 0.5s ease 0.2s, transform 0.5s ease 0.2s; /* Задержка перед исчезновением */
}
</style>
