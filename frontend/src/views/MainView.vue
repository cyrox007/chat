<template>
	<LeftSidebar :class="{ active: isLeftSidebarActive }" @close="closeLeftSidebar" :rooms="rooms"
		@switch-room="switchRoom" />
	<main class="chat-window">
		<header class="chat-window-header">
			<button class="toggle-left-sidebar" id="toggle-left-sidebar" aria-label="Открыть/закрыть левый сайдбар"
				@click="toggleLeftSidebar">
				<i class="fas fa-comments"></i>
			</button>
			<h2>{{ currentRoom.name || 'Нет выбранной комнаты' }}</h2>

			<button 
				class="toggle-right-sidebar" 
				id="toggle-right-sidebar" 
				aria-label="Открыть/закрыть правый сайдбар"
				@click="toggleRightSidebar"
				:disabled="!currentRoom.id">
				<i class="fas fa-info-circle"></i>
			</button>
		</header>

		<!-- Заглушка или окно чата -->
		<section v-if="!currentRoom.id && !isLoading" class="placeholder">
			<p>Выберите комнату, чтобы начать общение.</p>
		</section>

		<!-- Индикатор загрузки -->
		<Loader :isLoading="isLoading" />

		<div v-if="currentRoom.id && !isLoading" style="height: calc(100vh - 167px);">
			<section class="chat-window-body" id="chat-messages" style="height: 100%;">
				<Message v-for="(msg, index) in messages" :key="index" :message="msg" />
			</section>

			<section class="chat-window-inputs">
				<div class="input-container">
					<div v-if="isRecording" class="recording-indicator">Запись идет...</div>
					<button class="emoji-button">
						<i class="fas fa-smile"></i>
					</button>
					<input type="text" id="message-input" v-model="messageInput" @input="updateSendButton"
						placeholder="Введите сообщение" />
					<button class="attach-button" @click="selectFile">
						<i class="fas fa-paperclip"></i>
					</button>

					<input type="file" ref="fileInput" @change="handleFileUpload" style="display: none;" />

					<!-- Условная отрисовка кнопки -->
					<button class="send-button" id="send-message" @pointerdown="startRecording"
						@pointerup="stopRecording" @mouseleave="stopRecording" v-if="messageInput.trim() === ''">
						<i class="fas fa-microphone"></i>
					</button>

					<button class="send-button" id="send-message" v-else @click="sendMessage()">
						<i class="fas fa-paper-plane"></i>
					</button>
				</div>
			</section>
		</div>
	</main>
	<RightSidebar 
		v-if="currentRoom.id && !isLoading"
		:class="{ active: isRightSidebarActive }" 
		@close="closeRightSidebar" 
		:roomInfo="currentRoom" 
		:users="connectedUsers" />
</template>

<script setup>
import Loader from '@/components/Loader/index.vue';
import LeftSidebar from '@/components/LeftSidebar/index.vue';
import RightSidebar from '@/components/RightSidebar/index.vue';
import { ref, onMounted } from 'vue';
import Message from '@/components/Message/index.vue';

import RoomsService from '@/API/RoomsService';

const isLoading = ref(false); // Состояние загрузки
const messages = ref([]);
const messageInput = ref('');
const fileInput = ref(null);
const isLeftSidebarActive = ref(false);
const isRightSidebarActive = ref(false);
const currentRoom = ref({}); // Для хранения текущей комнаты
const rooms = ref([]); // Для хранения списка комнат
const connectedUsers = ref([]);
let ws = null;

// Загрузка списка комнат и сообщений
const loadRooms = async () => {
	try {
		const response = await RoomsService.get_rooms();

		// Проверяем, что в ответе есть поле rooms
		if (response.data.status === 'ok' && response.data.rooms) {
			rooms.value = response.data.rooms; // Присваиваем значение rooms
		} else {
			console.error('Неверный формат ответа:', data);
		}
	} catch (error) {
		console.error('Ошибка загрузки комнат:', error);
	}
};

// Загрузка данных комнаты
const loadRoomData = async (roomId) => {
	try {
		const response = await RoomsService.get_room(roomId);
		currentRoom.value = response.data.room;
		messages.value = response.data.messages;
	} catch (error) {
		console.error('Ошибка загрузки данных комнаты:', error);
	}
};

// Подключение к WebSocket
const connectToWebSocket = (roomId) => {
	const token = localStorage.getItem('access_token'); // Получаем токен из localStorage
	ws = new WebSocket(`ws://localhost:9001/ws/rooms/${roomId}?token=${token}`);
	ws.onopen = () => {
		console.log('Подключено к WebSocket');
	};
	ws.onmessage = (event) => {
		const data = JSON.parse(event.data);
		if (data.type === 'message') {
			messages.value.push(data.message);
		} else if (data.type === 'user_list') {
			connectedUsers.value = data.users;
		}
	};
	ws.onclose = () => {
		console.log('Соединение закрыто');
	};
};

const loadMessages = async (roomId) => {
	try {
		const response = await fetch(`/messages_${roomId}.json`); // Предполагается, что у вас есть отдельные файлы для каждой комнаты

		messages.value = await response.json();
	} catch (error) {
		console.error('Ошибка загрузки сообщений:', error);
	}
};

// Функция для переключения комнаты
const switchRoom = async (room) => {
    if (ws) {
        ws.close(); // Закрываем предыдущее соединение
    }

    // Очистка данных
    messages.value = [];
    connectedUsers.value = [];
    currentRoom.value = {};
    isLoading.value = true; // Включаем индикатор загрузки

    try {
        // Загрузка данных о комнате
        const roomData = await RoomsService.get_room(room.uid);
        currentRoom.value = roomData.data.room;

        // Подключение к WebSocket
        connectToWebSocket(room.uid);

        // Отключаем индикатор загрузки
        isLoading.value = false;

        // Показываем правый сайдбар
        isRightSidebarActive.value = true;
    } catch (error) {
        console.error('Ошибка загрузки данных комнаты:', error);
        isLoading.value = false; // Отключаем индикатор загрузки в случае ошибки
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

// Вызов функции загрузки комнат при монтировании компонента
onMounted(() => {
	loadRooms();
});

const recordedAudio = ref(null);
const isRecording = ref(false);
let mediaRecorder = null;
const errorMessage = ref('');

const sendMessage = async (file = null, messageType = 'text') => {
	// Проверяем, есть ли текст в поле ввода или записанное аудио
	if (messageInput.value.trim() !== '' || (recordedAudio.value && recordedAudio.value.size > 0)) {
		const newMessage = {
			avatar: 'https://i.pinimg.com/originals/d0/cf/a8/d0cfa8b3f2b9aa687e99cdd88bb82f10.jpg',
			username: 'Вы',
			timestamp: new Date().toLocaleTimeString(),
			content: messageInput.value,
			audio: recordedAudio.value ? URL.createObjectURL(recordedAudio.value) : null,
			file: file,
			type: messageType,
			sender: true,
			status: 'sending' // Статус отправки
		};

		messages.value.push(newMessage);

		// Очищаем поле ввода и сбрасываем записанное аудио
		messageInput.value = '';
		recordedAudio.value = null;

		// Здесь должна быть логика отправки на сервер
		try {
			const response = await sendToServer(newMessage); // Функция для отправки на сервер
			if (response.ok) {
				newMessage.status = 'sent'; // Обновляем статус на 'sent'
			} else {
				throw new Error('Ошибка отправки'); // Обрабатываем ошибку
			}
		} catch (error) {
			newMessage.status = 'failed'; // Обновляем статус на 'failed'
			errorMessage.value = 'Ошибка отправки сообщения: ' + error.message; // Отображаем ошибку
		}
	}
};

const startRecording = () => {
	if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
		navigator.mediaDevices.getUserMedia({ audio: true })
			.then(stream => {
				mediaRecorder = new MediaRecorder(stream);
				recordedAudio.value = []; // Сброс массива перед записью
				isRecording.value = true; // Устанавливаем флаг записи

				mediaRecorder.ondataavailable = (event) => {
					recordedAudio.value.push(event.data);
				};

				mediaRecorder.onstop = () => {
					const audioBlob = new Blob(recordedAudio.value, { type: 'audio/wav' });
					recordedAudio.value = audioBlob; // Сохраняем Blob вместо массива
					sendMessage(audioBlob); // Отправляем записанное аудио
					isRecording.value = false; // Сбрасываем флаг записи
				};

				mediaRecorder.start();
			})
			.catch(error => {
				console.error('Ошибка доступа к микрофону:', error);
			});
	} else {
		console.error('Ваш браузер не поддерживает запись аудио.');
	}
};

const stopRecording = () => {
	if (mediaRecorder) {
		mediaRecorder.stop();
		mediaRecorder = null; // Сбрасываем ссылку на mediaRecorder
	}
};

const selectFile = () => {
	fileInput.value.click(); // Открываем диалог выбора файла
};

const handleFileUpload = (event) => {
	const file = event.target.files[0]; // Получаем загруженный файл
	if (file) {
		// Проверяем тип файла, если нужно
		const validFileTypes = ['image/jpeg', 'image/png', 'video/mp4', 'audio/mpeg', 'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];

		if (validFileTypes.includes(file.type)) {
			sendMessage(file); // Отправляем файл вместе с сообщением
		} else {
			console.error('Неподдерживаемый тип файла:', file.type);
		}
	}
	fileInput.value.value = ''; // Сбрасываем input после загрузки
};

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

.chat-window-inputs {
	display: flex;
	align-items: center;
	padding: 10px;
	background-color: var(--bg-light);
	border-radius: 5px;
}

.chat-window-inputs .input-container {
	position: relative;
	width: 100%;
}

.chat-window-inputs .input-container input[type=text] {
	width: 100%;
	padding: 10px 40px;
	border: 1px solid var(--primary-color);
	border-radius: 5px;
	font-size: 16px;
}

.chat-window-inputs .input-container input[type=text]:focus {
	outline: none;
	border-color: var(--primary-color);
}

.chat-window-inputs .input-container button {
	position: absolute;
	background: none;
	border: none;
	cursor: pointer;
}

.chat-window-inputs .input-container button i {
	font-size: 20px;
	color: var(--primary-color);
}

.chat-window-inputs .input-container button:hover {
	color: var(--hover-color, #0056b3);
}

.chat-window-inputs .input-container .emoji-button {
	left: 10px;
	top: 50%;
	transform: translateY(-50%);
}

.chat-window-inputs .input-container .attach-button {
	right: 50px;
	top: 50%;
	transform: translateY(-50%);
}

.chat-window-inputs .input-container .send-button {
	right: 10px;
	top: 50%;
	transform: translateY(-50%);
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
