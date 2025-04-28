<script setup>
import { ref, onMounted, watch } from 'vue';
import HeaderComponent from './components/HeaderComponent/index.vue';
import ReplyNotifications from '@/components/Notifications/ReplyNotifications.vue';
import MessageNotifications from './components/Notifications/MessageNotifications.vue';
import { useStore } from 'vuex';
import AuthService from '@/API/AuthService';

const store = useStore();
const showErrorNotification = ref(false);

// Функция для проверки и обновления токена перед подключением
const ensureValidTokenAndConnect = async () => {
	if (!store.getters['isAuth']) return;
	try {
		// Проверяем и обновляем токен, если он устарел
		/* const response = await AuthService.getValidAccessToken();

		if (response.status !== 200) {
			throw new Error(`Ошибка при обновлении токена: ${response.statusText}`);
		} */

		// Подключаемся к чату, если есть активная комната
		if (store.getters['chat/getCurrentRoom']) {
			const roomId = store.getters['chat/getCurrentRoom'].uid;
			await store.dispatch('chat/connectSocket', roomId);
		}

		// Подключаемся к мессенджеру
		await store.dispatch('messenger/connectMessenger');
	} catch (error) {
		console.error('Ошибка при проверке или обновлении токена:', error);

		// Проверяем, является ли ошибка связанной с сервером (например, 500)
		if (error.response && [500, 502, 503, 504].includes(error.response.status)) {
			showErrorNotification.value = true;
		} else if (!error.response) {
			// Если нет ответа от сервера (например, проблемы с сетью)
			showErrorNotification.value = true;
		}
	}
};

onMounted(async () => {
	// Выполняем проверку токена и подключение
	await ensureValidTokenAndConnect();
});

// Отслеживаем изменения авторизации
watch(() => store.getters['isAuth'], (newVal) => {
	if (newVal) {
		// При авторизации проверяем токен и подключаемся
		ensureValidTokenAndConnect();
	} else {
		// При разлогинивании отключаем соединения
		store.dispatch('messenger/disconnectMessenger');
	}
});
</script>

<template>
	<div class="container chat-container">
		<ReplyNotifications />
		<MessageNotifications />
		<HeaderComponent />
		<transition name="fade">
			<div v-if="showErrorNotification" class="error-notification">
				<!-- Всплывающее уведомление об ошибке -->
				<p>Ошибка: сервер недоступен. Пожалуйста, проверьте соединение.</p>
			</div>
		</transition>

		<div class="mt-1">
			<RouterView />
		</div>
	</div>
</template>

<style scoped>
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
