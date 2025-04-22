<template>
	<CreateRoomModal :isShow="isCreateRoomeModalShow" @close="handleOpenCreateChatModal" @create-room-complete="loadRooms"/>
	<main class="chat-window">
		<LeftSidebar 
			:class="{ active: isLeftSidebarActive }" 
			@close="closeLeftSidebar" 
			:rooms="rooms"
			@switch-room="switchRoom" 
			:userRole="currentUser.global_role"
    		:userRating="currentUser.rating"
    		@open-create-chat-modal="handleOpenCreateChatModal"/>
		
		<div class="chat-content">
			<header class="chat-window-header">
				<button class="toggle-left-sidebar" aria-label="Открыть/закрыть левый сайдбар" @click="toggleLeftSidebar">
					<i class="fas fa-comments"></i>
				</button>
				<h2>{{ currentRoom?.name || 'Нет выбранной комнаты' }}</h2>
				<button class="toggle-right-sidebar" aria-label="Открыть/закрыть правый сайдбар" @click="toggleRightSidebar"
					:disabled="!currentRoom?.id">
					<i class="fas fa-info-circle"></i>
				</button>
			</header>
			<div v-if="currentRoom?.id && !isLoading" class="chat-container">
				<section id="chat-messages" ref="chatMessages" class="chat-window-body" >
					<Message 
						v-for="(msg, index) in messages" 
						:key="msg.uid || msg.tempId"
						:message="msg"
						:ref="index === messages.length - 1 ? 'lastMessage' : null"
						@reply="handleMessageReply"
					/>
				</section>
				<MessageComposer 
					ref="messageComposer"
					@send-message="handleSendMessage"
					:isDisabled="isUserMuted"
				/>
			</div>
			<section v-else-if="!isLoading" class="placeholder">
				<i class="fas fa-comments"></i>
				<p>Выберите комнату, чтобы начать общение.</p>
			</section>
		</div>
		
		<Loader :isLoading="isLoading" />
		<RightSidebar v-if="currentRoom?.id && !isLoading" :class="{ active: isRightSidebarActive }"
			@close="closeRightSidebar" :roomInfo="currentRoom" :users="connectedUsers" />
	</main>
	
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted, watch, nextTick } from 'vue';
import { useStore } from 'vuex';
import { v4 as uuidv4 } from 'uuid';
import DOMPurify from 'dompurify';

import Loader from '@/components/Loader/index.vue';
import LeftSidebar from '@/components/LeftSidebar/index.vue';
import RightSidebar from '@/components/RightSidebar/index.vue';
import Message from '@/components/Message/ChatMessage.vue';
import MessageComposer from '@/components/MessageComposer/index.vue';
import CreateRoomModal from '@/components/MainPageModals/CreateRoomModal.vue'

import RoomsService from '@/API/RoomsService';

// Инициализация хранилища
const store = useStore();

const isCreateRoomeModalShow = ref(false);

// Получаем данные из хранилища
const currentRoom = computed(() => store.getters['chat/getCurrentRoom']);
const messages = computed(() => store.getters['chat/getMessages']);

const connectedUsers = computed(() => store.getters['chat/getConnectedUsers']);

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
const isLeftSidebarActive = ref(false);
const isRightSidebarActive = ref(false);
const rooms = ref([]);
const messageComposer = ref(null);
const isUserMuted = computed(() => store.getters['chat/isUserMuted']);

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

// Обработчик ответа на сообщение
const handleMessageReply = (message) => {
  messageComposer.value?.setReply(message);
  scrollToBottom();
};

// Модифицированная функция отправки сообщения
const handleSendMessage = async (messageData) => {
	const sanitizedContent = DOMPurify.sanitize(messageData.content);

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
		reply_to_uid: messageData.reply_to_uid,
		status: 'sending',
	};

	store.dispatch('chat/sendMessage', messagePayload);
};

// Функция для переключения комнаты
const switchRoom = async (room) => {
	isLoading.value = true;
	try {
		const roomData = await RoomsService.get_room(room.uid);
		await store.dispatch('chat/switchRoom', {
			room: roomData.data.room,
			roomId: room.uid
		});
		isRightSidebarActive.value = true;
	} catch (error) {
		console.error('Ошибка загрузки данных комнаты:', error);
	} finally {
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
	if (currentRoom.value.id) {
		isRightSidebarActive.value = !isRightSidebarActive.value;
	}
};

// Функция для закрытия правого сайдбара
const closeRightSidebar = () => {
	isRightSidebarActive.value = false;
};

const handleOpenCreateChatModal = () => {
	isCreateRoomeModalShow.value = !isCreateRoomeModalShow.value;
}

const scrollToBottom = async () => {
    await nextTick(); // Ждём обновления DOM
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        //console.log('Scrolling to bottom...');
        chatMessages.scrollTop = chatMessages.scrollHeight;
        console.log('New scrollTop:', chatMessages.scrollTop);
    }
};

// Загрузка данных при монтировании
onMounted(async () => {
	loadRooms();
	if (currentRoom) {
		const savedRoom = rooms.value.find((room) => room.uid === currentRoom.uid);
		if (savedRoom) {
			await switchRoom(savedRoom);
		}
	}
});

// Очистка при размонтировании
onUnmounted(() => {
	//store.dispatch('chat/disconnectSocket');
});

watch(
	() => [...messages.value], // Создаем новый массив для триггера
	async () => {
		await nextTick();
		scrollToBottom();
	},
	{ deep: true }
);
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
	background-color: var(--bg-light); /* Используем переменную для фона */
	color: var(--text-light);
}
.chat-content {
	display: flex;
	flex-direction: column;
	width: 100%;
	background-color: var(--bg-light);
}
.chat-window-header {
	max-height: 40px;
	height: 40px;
	padding: 10px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	background-color: var(--primary-color); /* Используем основной цвет */
	border-bottom: 1px solid var(--primary-color); /* Используем основной цвет */
	color: white; /* Белый текст */
	box-shadow: var(--shadow-light); /* Добавляем легкую тень */
}
@media screen and (max-width: 400px) {
	.chat-window-header h2 {
		font-size: 1.15rem;
	}
}


.chat-window-header button {
	background: none;
	border: none;
	cursor: pointer;
	color: white; /* Белый текст */
	transition: color 0.2s ease; /* Плавное изменение цвета */
}

.chat-window-header button:hover {
	color: var(--primary-color-hover); /* Цвет при наведении */
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
	background-color: var(--bg-light); /* Используем переменную для фона */
}

.chat-window-body {
	min-height: 100px;
	flex: 1;
	overflow-y: auto;
	padding: 10px;
	background-color: var(--messenger-conversation-bg);
	color: var(--messenger-text);
	border: 1px solid var(--messenger-border);
	box-shadow: var(--shadow-light);
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
	flex-direction: column;
	align-items: center;
	justify-content: center;
	color: var(--text-light);
}

.placeholder i {
	font-size: 3rem;
	margin-bottom: 15px;
	color: var(--primary-color);
}

@media screen and (max-width: 370px) {
	.placeholder {
		font-size: 15px;
	}
}

/* Адаптивные стили для чата */
@media (max-width: 768px) {
	.message {
		max-width: 90%;
	}

	.reply-button {
		width: 30px;
		height: 30px;
		font-size: 1.1em;
	}

	.reply-preview .reply-content {
		max-width: 80vw;
	}
}

/* Анимация для кнопки ответа */
@keyframes pulse {
	0% {
		transform: scale(1);
	}

	50% {
		transform: scale(1.1);
	}

	100% {
		transform: scale(1);
	}
}

.message:active .reply-button {
	animation: pulse 0.3s ease;
}
</style>
