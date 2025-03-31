<template>
	<LeftSidebar :class="{ active: isLeftSidebarActive }" @close="closeLeftSidebar" :rooms="rooms"
		@switch-room="switchRoom" />
	<main class="chat-window">
		<header class="chat-window-header">
			<button class="toggle-left-sidebar" aria-label="Открыть/закрыть левый сайдбар" @click="toggleLeftSidebar">
				<i class="fas fa-comments"></i>
			</button>
			<h2>{{ chatStore.currentRoom?.name || 'Нет выбранной комнаты' }}</h2>
			<button class="toggle-right-sidebar" aria-label="Открыть/закрыть правый сайдбар" @click="toggleRightSidebar"
				:disabled="!chatStore.currentRoom?.id">
				<i class="fas fa-info-circle"></i>
			</button>
		</header>
		<div v-if="chatStore.currentRoom?.id && !isLoading" style="height: calc(100vh - 167px);">
			<section class="chat-window-body" id="chat-messages" style="height: 100%;">
				<Message v-for="(msg, index) in messages" :key="index" :message="msg" />
			</section>
				<MessageComposer @send-message="handleSendMessage" />
			
		</div>
		<section v-else-if="!isLoading" class="placeholder">
			<p>Выберите комнату, чтобы начать общение.</p>
		</section>
		<Loader :isLoading="isLoading" />
	</main>
	<RightSidebar v-if="chatStore.currentRoom?.id && !isLoading" :class="{ active: isRightSidebarActive }"
		@close="closeRightSidebar" :roomInfo="chatStore.currentRoom" :users="chatStore.connectedUsers" />
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useChatStore } from '@/stores/chat'; // Импортируем хранилище
import Loader from '@/components/Loader/index.vue';
import LeftSidebar from '@/components/LeftSidebar/index.vue';
import RightSidebar from '@/components/RightSidebar/index.vue';
import Message from '@/components/Message/index.vue';
import MessageComposer from '@/components/MessageComposer/index.vue';
import RoomsService from '@/API/RoomsService';
import UsersService from '@/API/UsersService';
import { WebSocketService } from '@/services/WebSocketService';
import CSRFService from '@/API/CSRFService';

// Инициализация хранилища
const chatStore = useChatStore();

// Состояния
const isLoading = ref(false);
const messages = ref([]);
const isLeftSidebarActive = ref(false);
const isRightSidebarActive = ref(false);
const rooms = ref([]);
const wsService = ref(null);

// Загрузка данных пользователей
const fetchUserData = async (userUids) => {
	try {
		await CSRFService.getCSRF();
		const response = await UsersService.get_users_by_uids(userUids);
		if (response.data.status === 'ok') {
			return response.data.users;
		}
		return [];
	} catch (error) {
		console.error('Ошибка загрузки данных пользователей:', error);
		return [];
	}
};

// Загрузка списка комнат
const loadRooms = async () => {
	try {
		const response = await RoomsService.get_rooms();
		if (response.data.status === 'ok' && response.data.rooms) {
			rooms.value = response.data.rooms;
		}
	} catch (error) {
		console.error('Ошибка загрузки комнат:', error);
	}
};

// Подключение к WebSocket
const connectToWebSocket = (roomId) => {
	const token = localStorage.getItem('access_token');
	if (!token) {
		console.error('Токен не найден');
		return;
	}

	wsService.value = new WebSocketService(roomId, token);
	const socket = wsService.value.connect();

	socket.onopen = () => {
		console.log('Подключено к WebSocket');
	};

	socket.onmessage = async (event) => {
		const data = JSON.parse(event.data);
		if (data.type === 'message') {
			messages.value.push(data.message);
		} else if (data.type === 'user_list') {
			const usersData = await fetchUserData(data.users);
			chatStore.setConnectedUsers(usersData); // Сохраняем пользователей в хранилище
		}
	};

	socket.onclose = () => {
		console.log('Соединение закрыто');
	};

	socket.onerror = (error) => {
		console.error('Ошибка WebSocket:', error);
	};
};

const disconnectFromWebSocket = () => {
	if (wsService.value) {
		wsService.value.disconnect();
		wsService.value = null; // Очищаем ссылку на сервис
	}
};

// Функция для сохранения UID комнаты
const saveCurrentRoom = (roomUid) => {
	localStorage.setItem('currentRoomUid', roomUid);
};

// Функция для загрузки UID комнаты
const loadCurrentRoom = () => {
	return localStorage.getItem('currentRoomUid');
};

// Функция для переключения комнаты
const switchRoom = async (room) => {
	if (wsService.value) {
		wsService.value.disconnect();
	}

	// Очистка данных
	messages.value = [];
	chatStore.clearCurrentRoom();
	isLoading.value = true;

	try {
		const roomData = await RoomsService.get_room(room.uid);
		chatStore.setCurrentRoom(roomData.data.room); // Сохраняем комнату в хранилище
		connectToWebSocket(room.uid);
		isLoading.value = false;
		isRightSidebarActive.value = true;
	} catch (error) {
		console.error('Ошибка загрузки данных комнаты:', error);
		isLoading.value = false;
	}
};

// Функция для переключения левого сайдбара
const toggleLeftSidebar = () => {
	isLeftSidebarActive.value = !isLeftSidebarActive.value;
	if (isRightSidebarActive.value) {
		isRightSidebarActive.value = false; // Закрываем правый сайдбар, если он открыт
	}
};

// Функция для закрытия левого сайдбара
const closeLeftSidebar = () => {
	isLeftSidebarActive.value = false;
};

// Функция для переключения правого сайдбара
const toggleRightSidebar = () => {
	if (currentRoom.id) {
		isRightSidebarActive.value = !isRightSidebarActive.value;
	}
};

// Функция для закрытия правого сайдбара
const closeRightSidebar = () => {
	isRightSidebarActive.value = false;
};

// Загрузка данных при монтировании
onMounted(async () => {
	loadRooms();
	if (chatStore.currentRoom) {
		const savedRoom = rooms.value.find((room) => room.uid === chatStore.currentRoom.uid);
		if (savedRoom) {
			await switchRoom(savedRoom);
		}
	}
});
</script>

<style>
.chat-window-body {
	flex: 1;
	overflow-y: auto;
	padding: 10px;
	background-color: #f0f0f0;
	/* max-height: calc(100vh - 165px); */
}

.chat-window-body .message {
	display: flex;
	align-items: flex-start;
	margin-bottom: 10px;
	flex-direction: column;
	padding: 5px;
}

.chat-window-body .message-header {
	display: flex;
	align-items: center;
	max-height: 40px;
}

.chat-window-body .message-header .avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	margin-right: 10px;
}

.chat-window-body .message-header .user-info {
	display: flex;
	flex-direction: column;
}

.chat-window-body .message-header .user-info .timestamp {
	font-size: 0.8em;
	color: #888;
}

.chat-window-body .message-body {
	padding: 10px;
	border-radius: 5px;
	max-width: 70%;
	position: relative;
}

.chat-window-body .message-body.image-message img.message-image {
	max-width: 100%;
	border-radius: 5px;
}

.chat-window-body .message-body.image-message .image-caption {
	display: block;
	font-size: 0.9em;
	color: #555;
	margin-top: 5px;
}

.chat-window-body .message-body.video-message video.message-video {
	width: 100%;
	border-radius: 5px;
}

.chat-window-body .message-body.audio-message audio.message-audio {
	width: 100%;
	border-radius: 5px;
}

.chat-window-body .message-body.document-message {
	background-color: #e8e8e8;
	padding: 10px;
	border-radius: 5px;
	display: flex;
	align-items: center;
}

.chat-window-body .message-body.document-message .document-icon {
	font-size: 24px;
	margin-right: 10px;
}

.chat-window-body .message-body.document-message .document-name {
	font-weight: bold;
}

.chat-window-body .message-body .message-image {
	max-width: 100%;
	/* Ограничение ширины изображения */
	height: auto;
	/* Автоматическая высота для сохранения пропорций */
	border-radius: 5px;
	/* Закругление углов изображения */
	margin-top: 5px;
	/* Отступ сверху для изображения */
}

.chat-window-body .message-body .image-caption {
	font-size: 0.9em;
	/* Размер шрифта для подписи к изображению */
	color: #555;
	/* Цвет подписи */
	margin-top: 3px;
	/* Отступ сверху для подписи */
}

.chat-window-body .message-body .message-video {
	max-width: 100%;
	/* Ограничение ширины видео */
	height: auto;
	/* Автоматическая высота для сохранения пропорций */
	border-radius: 5px;
	/* Закругление углов видео */
	margin-top: 5px;
	/* Отступ сверху для видео */
}

.chat-window-body .message-body .message-audio {
	margin-top: 5px;
	/* Отступ сверху для аудио */
	width: 100%;
	/* Ширина аудио плеера */
}

.chat-window-body .message-body .audio-message {
	background-color: #e0f7fa;
	/* Цвет фона для аудио сообщений */
}

.chat-window-body .message-body .video-message {
	background-color: #ffe0b2;
	/* Цвет фона для видео сообщений */
}

.chat-window-body .message-body .image-message {
	background-color: #fce4ec;
	/* Цвет фона для изображений */
}

.chat-window-body .message.sender {
	background-color: var(--sender-bg);
	margin-left: auto;
}

.chat-window-body .message.other-user {
	background-color: var(--other-user-bg);
}

.chat-window-body .message.mention {
	background-color: var(--mention-bg);
	border: 1px solid var(--mention-border);
	font-weight: bold;
}

.placeholder {
	display: flex;
	justify-content: center;
	align-items: center;
	height: 100%;
	text-align: center;
	color: #888;
	font-size: 1.2rem;
	font-style: italic;
	background: aliceblue;
}
</style>
