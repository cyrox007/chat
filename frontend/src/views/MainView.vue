<template>
	<LeftSidebar 
		:class="{ active: isLeftSidebarActive }" 
		@close="closeLeftSidebar" 
		:rooms="rooms" 
        @switch-room="switchRoom"/>
	<main class="chat-window">
		<header class="chat-window-header">
			<button class="toggle-left-sidebar" id="toggle-left-sidebar" aria-label="Открыть/закрыть левый сайдбар"
				@click="toggleLeftSidebar">
				<i class="fas fa-comments"></i>
			</button>
			<h2>{{ currentRoom.name }}</h2> <!-- Отображаем название текущей комнаты -->

			<button class="toggle-right-sidebar" id="toggle-right-sidebar" aria-label="Открыть/закрыть правый сайдбар"
				@click="toggleRightSidebar">
				<i class="fas fa-info-circle"></i>
			</button>
		</header>
		<section class="chat-window-body" id="chat-messages">
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
				<button class="send-button" 
						id="send-message" 
						@pointerdown="startRecording" 
						@pointerup="stopRecording" 
						@mouseleave="stopRecording" 
						v-if="messageInput.trim() === ''">
					<i class="fas fa-microphone"></i>
				</button>

				<button class="send-button" id="send-message" v-else 
					@click="sendMessage()">
					<i class="fas fa-paper-plane"></i>
				</button>
			</div>
		</section>

	</main>
	<RightSidebar :class="{ active: isRightSidebarActive }" @close="closeRightSidebar" />
</template>

<script setup>
import LeftSidebar from '@/components/LeftSidebar/index.vue';
import RightSidebar from '@/components/RightSidebar/index.vue';
import { ref, onMounted } from 'vue';
import Message from '@/components/Message/index.vue';

import RoomsService from '@/API/RoomsService';

const messages = ref([]);
const messageInput = ref('');
const fileInput = ref(null);
const isLeftSidebarActive = ref(false);
const isRightSidebarActive = ref(false);
const currentRoom = ref({}); // Для хранения текущей комнаты
const rooms = ref([]); // Для хранения списка комнат

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

const loadMessages = async (roomId) => {
    try {
        const response = await fetch(`/messages_${roomId}.json`); // Предполагается, что у вас есть отдельные файлы для каждой комнаты
        
        messages.value = await response.json();
    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);
    }
};

// Функция для переключения комнаты
const switchRoom = (room) => {
    currentRoom.value = room; // Устанавливаем текущую комнату
    loadMessages(room.id); // Загружаем сообщения для выбранной комнаты
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
    isRightSidebarActive.value = !isRightSidebarActive.value;
    if (isLeftSidebarActive.value) {
        isLeftSidebarActive.value = false; // Закрываем левый сайдбар, если он открыт
    }
};

// Функция для закрытия правого сайдбара
const closeRightSidebar = () => {
    isRightSidebarActive.value = false;
};

// Вызов функции загрузки комнат при монтировании компонента
onMounted(() => {
    loadRooms();
    if (rooms.value.length > 0) {
		debugger;
        switchRoom(rooms.value[0].id); // Загружаем сообщения для первой комнаты по умолчанию
    }
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