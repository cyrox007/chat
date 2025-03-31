<template>
    <section class="chat-window-inputs">
        <div class="input-container">
            <!-- Эмодзи -->
            <button class="emoji-button" @click="toggleEmojiPicker">
                <i class="fas fa-smile"></i>
            </button>

            <!-- Поле ввода текста -->
            <input
                type="text"
                v-model="messageInput"
                placeholder="Введите сообщение"
                @keydown.enter="sendMessage"
            />

            <!-- Кнопка для отправки файла -->
            <button class="attach-button" @click="selectFile">
                <i class="fas fa-paperclip"></i>
            </button>
            <input type="file" ref="fileInput" @change="handleFileUpload" style="display: none;" />

            <!-- Кнопка для записи голосового сообщения -->
            <button
                class="record-button"
                @pointerdown="startRecording"
                @pointerup="stopRecording"
                @mouseleave="stopRecording"
                v-if="messageInput.trim() === ''"
            >
                <i class="fas fa-microphone"></i>
            </button>

            <!-- Кнопка для отправки текстового сообщения -->
            <button class="send-button" @click="sendMessage" v-else>
                <i class="fas fa-paper-plane"></i>
            </button>
        </div>

        <!-- Индикатор записи голоса -->
        <div v-if="isRecording" class="recording-indicator">Запись идет...</div>
    </section>
</template>

<script setup>
import { ref } from 'vue';

const messageInput = ref('');
const isRecording = ref(false);
const recordedAudio = ref(null);
const mediaRecorder = ref(null);
const fileInput = ref(null);

// Функция для начала записи голоса
const startRecording = async () => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder.value = new MediaRecorder(stream);
            recordedAudio.value = [];

            mediaRecorder.value.ondataavailable = (event) => {
                recordedAudio.value.push(event.data);
            };

            mediaRecorder.value.onstop = () => {
                const audioBlob = new Blob(recordedAudio.value, { type: 'audio/wav' });
                sendMessage(audioBlob, 'audio');
            };

            mediaRecorder.value.start();
            isRecording.value = true;
        } catch (error) {
            console.error('Ошибка доступа к микрофону:', error);
        }
    } else {
        console.error('Ваш браузер не поддерживает запись аудио.');
    }
};

// Функция для остановки записи голоса
const stopRecording = () => {
    if (mediaRecorder.value) {
        mediaRecorder.value.stop();
        mediaRecorder.value.stream.getTracks().forEach(track => track.stop());
        isRecording.value = false;
    }
};

// Функция для выбора файла
const selectFile = () => {
    fileInput.value.click();
};

// Обработка загруженного файла
const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        sendMessage(file, 'file');
    }
    fileInput.value.value = '';
};

// Отправка сообщения
const sendMessage = (content = null, type = 'text') => {
    if (!content && messageInput.value.trim() === '') return;

    const newMessage = {
        content: content || messageInput.value,
        type: type,
        timestamp: new Date().toLocaleTimeString(),
        status: 'sending',
    };

    // Логика отправки через WebSocket
    // ws.send(JSON.stringify(newMessage));

    messageInput.value = ''; // Очищаем поле ввода
};
</script>

<style scoped>
.chat-window-inputs {
    display: flex;
    flex-direction: column;
    padding: 10px;
    background-color: var(--bg-light);
    border-radius: 5px;
}

.input-container {
    display: flex;
    align-items: center;
    position: relative;
}

.input-container input[type='text'] {
    flex: 1;
    padding: 10px;
    border: 1px solid var(--primary-color);
    border-radius: 5px;
    font-size: 16px;
}

.input-container button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 20px;
    color: var(--primary-color);
    margin: 0 5px;
}

.recording-indicator {
    margin-top: 5px;
    font-size: 0.9em;
    color: #888;
}
</style>