<script setup>
import { ref, onMounted, onBeforeUnmount, provide } from 'vue'
import { RouterView } from 'vue-router'
import HeaderComponent from './components/HeaderComponent/index.vue'
import $api from '@/API/index.js' // Импортируйте ваш экземпляр Axios

const serverAvailable = ref(true) // Состояние для проверки доступности сервера
const showErrorNotification = ref(false); // Состояние для управления отображением уведомления

// Функция для проверки доступности сервера
const checkServerAvailability = async () => {
    try {
        const response = await $api.get('/health'); // Замените на ваш эндпоинт для проверки состояния сервера
		
        if (response.status !== 200) {
            throw new Error('Сервер недоступен');
        }
    } catch (error) {
        serverAvailable.value = false; // Устанавливаем состояние в false, если сервер недоступен
        showErrorNotification.value = true; // Показываем уведомление об ошибке
        setTimeout(() => {
            showErrorNotification.value = false; // Скрываем уведомление через 5 секунд
        }, 5000); // Задержка в 5 секунд
    }
}
const socket = ref(null);
// Инициализация WebSocket
const initializeWebSocket = () => {
    socket.value = new WebSocket('ws://your-websocket-server-url');

    socket.value.onopen = () => {
        console.log('Соединение с WebSocket установлено');
    };

    socket.value.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
            messages.value.push(data.message);
        } else if (data.type === 'status') {
            userStatus.value[data.userId] = data.status;
        }
    };

    socket.value.onclose = () => {
        console.log('Соединение с WebSocket закрыто');
    };

    socket.value.onerror = (error) => {
        console.error('Ошибка WebSocket:', error);
    };
};

// Проверяем доступность сервера и инициализируем WebSocket при монтировании компонента
onMounted(() => {
    checkServerAvailability();
    initializeWebSocket();
});

// Закрытие WebSocket при размонтировании компонента
onBeforeUnmount(() => {
    if (socket.value) {
        socket.value.close();
    }
});

// Предоставляем WebSocket и состояния для дочерних компонентов
provide('websocket', socket);
//provide('messages', messages);
//provide('userStatus', userStatus);
</script>

<template>
    <div class="container chat-container">
        <HeaderComponent />

        <!-- Всплывающее уведомление об ошибке -->
        <transition name="fade">
            <div v-if="showErrorNotification" class="error-notification">
                <p>Ошибка: сервер недоступен. Пожалуйста, проверьте соединение и перезагрузите приложение. Если ошибка повторится, попробуйте позже.</p>
            </div>
        </transition>

        <div class="row chat-wrapper">
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

.fade-enter-active, .fade-leave-active {
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
