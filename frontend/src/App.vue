<script setup>
import { ref, onMounted, watch } from 'vue';
import HeaderComponent from './components/HeaderComponent/index.vue';
import ReplyNotifications from '@/components/Notifications/ReplyNotifications.vue';
import { useStore } from 'vuex';

const store = useStore();
const showErrorNotification = ref(false);

onMounted(async () => {
	// Восстановление соединения при наличии активной комнаты
	if (store.getters['chat/getCurrentRoom']) {
		const roomId = store.getters['chat/getCurrentRoom'].uid;
		store.dispatch('chat/connectSocket', roomId);
	}

	// Подключаемся к мессенджеру
	store.dispatch('messenger/connectMessenger');
});

// Отслеживаем изменения авторизации
watch(() => store.getters['isAuth'], (newVal) => {
	if (newVal) {
		store.dispatch('messenger/connectMessenger');
	} else {
		store.dispatch('messenger/disconnectMessenger');
	}
});
</script>

<template>
	<div class="container chat-container">
		<ReplyNotifications />
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
