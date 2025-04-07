<template>
	<main class="chat-window">
		<LeftSidebar :class="{ active: isLeftSidebarActive }" @close="closeLeftSidebar" :rooms="rooms"
			@switch-room="switchRoom" />
		
		<div class="chat-content">
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
				<section id="chat-messages" ref="chatMessages" class="chat-window-body" >
					<Message 
						v-for="(msg, index) in messages" 
						:key="msg.uid || msg.tempId"
						:message="msg"
						:ref="index === messages.length - 1 ? 'lastMessage' : null"
					/>
				</section>
				<MessageComposer @send-message="handleSendMessage" />
			</div>
			<section v-else-if="!isLoading" class="placeholder">
				<p>Выберите комнату, чтобы начать общение.</p>
			</section>
		</div>
		
		<Loader :isLoading="isLoading" />
		<RightSidebar v-if="chatStore.currentRoom?.id && !isLoading" :class="{ active: isRightSidebarActive }"
			@close="closeRightSidebar" :roomInfo="chatStore.currentRoom" :users="chatStore.connectedUsers" />
	</main>
	
</template>

<script setup>
import { ref, reactive, onMounted, computed, onUnmounted, watch, nextTick } from 'vue';
import { useStore } from 'vuex';
import { v4 as uuidv4 } from 'uuid';
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
const store = useStore();

// Получаем состояние чата из Vuex
const chatStore = reactive({
	currentRoom: computed(() => store.getters['chat/getCurrentRoom']),
	connectedUsers: computed(() => store.getters['chat/getConnectedUsers']),
});

// Функции для изменения состояния
const setCurrentRoom = (room) => store.dispatch('chat/updateCurrentRoom', room);
const clearCurrentRoom = () => store.commit('chat/clearCurrentRoom');
const setConnectedUsers = (users) => store.dispatch('chat/updateConnectedUsers', users);

// Получаем данные текущего пользователя из хранилища
const currentUser = computed(() => {
	const user = store.getters.getUser || {
		uid: null,
		username: 'Неизвестный пользователь',
		avatar: '/images/default-avatar.png',
	};
	return user;
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

const sanitizeMessage = (messageData) => {
	// Очищаем текстовое поле
	// Возвращаем очищенные данные
	return DOMPurify.sanitize(messageData)
};

const handleSendMessage = async (messageData) => {
	const sanitizedContent = sanitizeMessage(messageData.content);
	const messagePayload = {
		frontId: uuidv4(),
		content: sanitizedContent || '',
		content_type: messageData.content_type,
		media_metadata: messageData.media_metadata,
		sender: {
			uid: currentUser.value.uid,
			name: currentUser.value.username,
			avatar: currentUser.value.avatar,
		},
		created_at: new Date().toISOString(),
		status: 'sending',
	};

	try {
		console.log(messagePayload);

		// Отправляем сообщение через WebSocket
		if (!wsService.value || !wsService.value.send) {
			console.error('WebSocket не подключен или метод send не определён');
			return;
		}
		messages.value.push(messagePayload);
		wsService.value.send(messagePayload);
	} catch (error) {
		console.error('Ошибка отправки сообщения:', error);
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
			if (data.sender?.uid === currentUser.value.uid) {
				// Обновляем наше сообщение
				const messageIndex = messages.value.findIndex(msg => msg.frontId === data.frontId);
				if (messageIndex !== -1) {
					messages.value[messageIndex] = {
						...messages.value[messageIndex],
						uid: data.uid,
						status: 'sent',
					};
				}
			} else {
				// Добавляем сообщение от другого пользователя
				messages.value.push(data);
				await nextTick(); // Ждём обновления DOM
            	scrollToBottom();
			}
		} else if (data.type === 'user_list') {
			// Обработка списка пользователей
			const usersData = await fetchUserData(data.users);
			setConnectedUsers(usersData); // Сохраняем пользователей в хранилище
		} else if (data.type === 'initial_data') {
			// Проверяем структуру данных
			if (!Array.isArray(data.messages)) {
				console.error('Некорректные данные initial_data:', data.messages);
				return;
			}

			// Добавляем начальные данные в начало массива
			messages.value.unshift(...data.messages.reverse());
			scrollToBottom();
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
	messages.value = [];
	clearCurrentRoom(); // Очистка текущей комнаты
	isLoading.value = true;

	try {
		const roomData = await RoomsService.get_room(room.uid);
		setCurrentRoom(roomData.data.room); // Устанавливаем новую комнату
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
	if (chatStore.currentRoom.id) {
		isRightSidebarActive.value = !isRightSidebarActive.value;
	}
};

// Функция для закрытия правого сайдбара
const closeRightSidebar = () => {
	isRightSidebarActive.value = false;
};

const isScrolledToBottom = () => {
	const chatMessages = document.getElementById('chat-messages');
	if (!chatMessages) return false;

	const scrollHeight = chatMessages.scrollHeight;
	const scrollTop = chatMessages.scrollTop;
	const clientHeight = chatMessages.clientHeight;

	console.log('scrollHeight:', scrollHeight);
	console.log('scrollTop:', scrollTop);
	console.log('clientHeight:', clientHeight);

	// Проверяем, находится ли скролл внизу
	const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 5;
	console.log('Is scrolled to bottom:', isAtBottom);

	return isAtBottom;
};

const isLastMessageVisible = () => {
	const chatMessages = document.getElementById('chat-messages');
	const lastMessage = document.querySelector('.message:last-child'); // Или используйте ref

	if (!chatMessages || !lastMessage) return false;

	// Получаем позицию последнего сообщения относительно контейнера
	const messageRect = lastMessage.getBoundingClientRect();
	const containerRect = chatMessages.getBoundingClientRect();

	// Проверяем, находится ли сообщение в видимой области контейнера
	return (
		messageRect.bottom <= containerRect.bottom + 50 && // Допуск 50px
		messageRect.top >= containerRect.top
	);
};

const scrollToBottom = async () => {
    await nextTick(); // Ждём обновления DOM
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        console.log('Scrolling to bottom...');
        chatMessages.scrollTop = chatMessages.scrollHeight;
        console.log('New scrollTop:', chatMessages.scrollTop);
    }
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

watch(messages, async () => {
	await nextTick();
	scrollToBottom();
}, { deep: true });
</script>

<style scoped>
.chat-window {
	height: calc(100vh - (54px + 5px));
	
	width: 100%;
	flex: 0 0 100%;
	display: flex;
	flex-direction: row;
	flex-wrap: nowrap;
	overflow-x: hidden;
}
.chat-content {
	display: flex;
	flex-direction: column;
	width: 100%;
}
.chat-window-header {
	max-height: 40px;
	height: 40px;
	padding: 10px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	background-color: var(--primary-color);
	border-bottom: 1px solid var(--primary-color);
	color: #fff;
}

.chat-window-header button {
	background: none;
	border: none;
	cursor: pointer;
	color: #fff;
}

.chat-window-header button:disabled {
	cursor:auto;
	opacity: 0.8;
}

.chat-container {
	flex: 1 1 100%;

	display: flex;
	flex-direction: column;
	
	overflow: hidden;
}

.chat-window-body {
	min-height: 100px;
	flex: 1;
	overflow-y: auto;
	padding: 10px;
	background-color: #f0f0f0;
}

/* Стили для компонента ввода данных */
.message-composer {
	flex-shrink: 0; /* Предотвращает сжатие компонента */
	padding: 10px;
	background-color: var(--bg-light);
	border-top: 1px solid var(--primary-color);
}

.placeholder {
	flex: 1;
	height: 100%;
	width: 100%;
	background: var(--bg-light);
	display: flex;
	align-items: center;
	justify-content: center;
}
</style>
