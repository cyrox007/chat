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
		<div v-if="chatStore.currentRoom?.id && !isLoading" class="chat-container">
			<section class="chat-window-body" id="chat-messages">
				<Message 
					v-for="(msg, index) in messages" 
					:key="msg.uid || msg.tempId"
					:message="msg"
				/>
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
import { ref, onMounted, computed, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import { v4 as uuidv4 } from 'uuid';
import { useChatStore } from '@/stores/chat'; // Импортируем хранилище
import DOMPurify from 'dompurify';
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
const store = useStore();

// Получаем данные текущего пользователя из хранилища
const currentUser = computed(() => {
	return store.getters.getUser || {
		uid: null,
		username: 'Неизвестный пользователь',
		avatar: '/images/default-avatar.png',
	};
});

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

const determineContentType = (messageData) => {
	if (messageData.audio) return 'audio';
	if (messageData.files.length > 0) return 'file';
	if (/[\uD800-\uDBFF][\uDC00-\uDFFF]/.test(messageData.text)) return 'sticker';
	return 'text';
};

const sanitizeMessage = (messageData) => {
	// Очищаем текстовое поле
	const sanitizedText = DOMPurify.sanitize(messageData.text);

	// Очищаем имена файлов
	const sanitizedFiles = messageData.files.map(file => ({
		name: DOMPurify.sanitize(file.name),
	}));

	// Возвращаем очищенные данные
	return {
		content: sanitizedText,
		files: sanitizedFiles,
		audio: messageData.audio || null,
	};
};

const handleSendMessage = async (messageData) => {
	const sanitizedMessage = sanitizeMessage(messageData);

	const messagePayload = {
		tempId: uuidv4(), // Временный ID для отслеживания на фронтенде
		content: sanitizedMessage.content || '', // Текст или ссылка на медиа
		content_type: determineContentType(sanitizedMessage), // Тип контента
		sender: {
			uid: currentUser.value.uid,
			name: currentUser.value.username,
			avatar: currentUser.value.avatar,
		},
		created_at: new Date().toISOString(), // Время создания
		status: 'sending', // Статус: "отправляется"
	};

	try {
		console.log(messagePayload);
		
		/* if (!wsService.value || !wsService.value.send) {
			console.error('WebSocket не подключен или метод send не определён');
			return;
		}

		// Отправляем сообщение через WebSocket
		wsService.value.send(messagePayload);

		// Добавляем сообщение в массив
		messages.value.push({
			...messagePayload,
		});

		// Подписываемся на ответ от сервера
		wsService.value.onMessage((serverMessage) => {
			if (serverMessage.type === 'message' && serverMessage.tempId) {
				// Находим сообщение по tempId
				const messageIndex = messages.value.findIndex(msg => msg.tempId === serverMessage.tempId);
				if (messageIndex !== -1) {
					// Обновляем сообщение данными с сервера
					messages.value[messageIndex] = {
						...messages.value[messageIndex],
						uid: serverMessage.uid, // Окончательный ID с сервера
						status: 'sent', // Статус: "отправлено"
					};
				}
			}
		}); */

	} catch (error) {
		console.error('Ошибка отправки сообщения:', error);

		// Обновляем статус в случае ошибки
		const messageIndex = messages.value.findIndex(msg => msg.tempId === messagePayload.tempId);
		if (messageIndex !== -1) {
			messages.value[messageIndex].status = 'error'; // Статус: "ошибка"
		}
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

	// Подписываемся на входящие сообщения
	wsService.value.onMessage(async (data) => {
		console.log("Полученные данные от сервера:", data);

		if (data.type === 'message') {
			// Добавляем новое сообщение в конец массива
			messages.value.push(data); // push добавляет в конец массива
		} else if (data.type === 'user_list') {
			const usersData = await fetchUserData(data.users);
			chatStore.setConnectedUsers(usersData); // Сохраняем пользователей в хранилище
		} else if (data.type === 'initial_data') {
			// Проверяем структуру данных
			if (!Array.isArray(data.messages)) {
				console.error('Некорректные данные initial_data:', data.messages);
				return;
			}

			// Добавляем начальные данные в начало массива
			messages.value.unshift(...data.messages.reverse());
		}
	});
};

const disconnectFromWebSocket = () => {
	if (wsService.value) {
		wsService.value.disconnect();
		wsService.value = null; // Очищаем ссылку на сервис
		messages.value = null; // Отчищаем массив сообщений
	}
};

// Функция для переключения комнаты
const switchRoom = async (room) => {
	if (wsService.value) disconnectFromWebSocket();

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

onUnmounted(() => {
	if (wsService.value) wsService.value.disconnect();
});
</script>

<style scoped>
.chat-window {
	display: flex;
	flex-direction: column;
	height: 100%; /* Занимает всю доступную высоту */
}

.chat-window-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 10px;
	background-color: var(--primary-color);
	border-bottom: 1px solid var(--primary-color);
}

.chat-container {
	display: flex;
	flex-direction: column;
	flex: 1;
	/* Занимает всё оставшееся пространство */
	overflow: hidden;
	/* Предотвращает прокрутку всего контейнера */
}

.chat-window-body {
	flex: 1;
	/* Занимает всё доступное пространство */
	overflow-y: auto;
	/* Добавляет прокрутку только для окна сообщений */
	padding: 10px;
	background-color: #f0f0f0;
}

/* Стили для компонента ввода данных */
.message-composer {
	flex-shrink: 0;
	/* Предотвращает сжатие компонента */
	padding: 10px;
	background-color: var(--bg-light);
	border-top: 1px solid var(--primary-color);
}

.placeholder {
	flex: 1;
	height: 100%;
	background: var(--bg-light);
	display: flex;
	align-items: center;
	justify-content: center;
}
</style>
