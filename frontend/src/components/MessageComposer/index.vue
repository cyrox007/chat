<template>
	<div class="chat-window-inputs">
		<!-- Отображение выбранных файлов -->
		<div class="file-preview" v-if="selectedFiles.length > 0">
			<div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
				<span v-if="isImage(file)" class="file-thumbnail">
					<img :src="getThumbnail(file)" alt="Thumbnail" />
				</span>
				<span v-else class="file-icon">
					<i class="fas fa-file"></i>
				</span>
				<span class="file-name">{{ file.name }}</span>
				<button class="remove-file" @click="removeFile(index)">
					<i class="fas fa-times"></i>
				</button>
			</div>
		</div>

		<!-- Индикатор записи голоса и кнопка записи -->
		<div v-if="isRecording" class="recording-area">
			<div class="recording-indicator">
				Запись идет...
				<div class="audio-level-bar">
					<div class="audio-level-fill" :style="{ width: `${audioLevel * 100}%` }"></div>
				</div>
			</div>
			<button class="record-button" @pointerdown="startRecording" @mouseup="stopRecording"
				@mouseleave="stopRecording">
				<i class="fas fa-microphone"></i>
			</button>
		</div>

		<!-- Поле ввода текста -->
		<div class="input-container" v-if="!isRecording && !isAudioRecorded">
			<input type="text" v-model="messageInput" placeholder="Введите сообщение" @keydown.enter="prepareMessage" />
			<button class="emoji-button" @click="toggleEmojiPicker">
				<i class="fas fa-smile"></i>
			</button>
			<button class="attach-button" @click="selectFile">
				<i class="fas fa-paperclip"></i>
			</button>
			<!-- Кнопка записи или отправки -->
			<button class="record-button" @pointerdown="startRecording" @mouseup="stopRecording"
				@mouseleave="stopRecording"
				v-if="messageInput.trim() === '' && selectedFiles.length === 0 && !isRecording">
				<i class="fas fa-microphone"></i>
			</button>
			<button class="send-button" @click="prepareMessage" v-else>
				<i class="fas fa-paper-plane"></i>
			</button>
		</div>

		<!-- Плеер с кнопкой отправки -->
		<div class="audio-preview" v-else-if="isAudioRecorded">
			<audio controls :src="audioUrl"></audio>
			<div class="controls">
				<button class="remove-audio" @click="clearAudio">
					<i class="fas fa-times"></i>
				</button>
				<button class="send-button" @click="prepareMessage">
					<i class="fas fa-paper-plane"></i>
				</button>
			</div>
		</div>
		<!-- Скрытый элемент для выбора файлов -->
		<input type="file" ref="fileInput" @change="handleFileUpload" multiple style="display: none;" />
	</div>
</template>

<script setup>
import { ref, defineEmits, onUnmounted } from 'vue';

// Состояния
const messageInput = ref('');
const isRecording = ref(false);
const recordedAudio = ref(null);
const mediaRecorder = ref(null);
const selectedFiles = ref([]);
const isEmojiPickerVisible = ref(false);
const audioUrl = ref(null);
const audioContext = ref(null);
const analyser = ref(null);
const audioLevel = ref(0); // Уровень громкости
const isAudioRecorded = ref(false); // Флаг для отображения плеера

const emit = defineEmits(['send-message']);

// Эмодзи
const emojis = ['😊', '😂', '❤️', '👍', '🎉', '🤔', '😎', '😢', '🔥', '🚀'];

// Функция для проверки, является ли файл изображением
const isImage = (file) => {
	return file.type.startsWith('image/');
};

// Функция для получения миниатюры изображения
const getThumbnail = (file) => {
	return URL.createObjectURL(file);
};

// Функция для выбора файла
const selectFile = () => {
	document.querySelector('input[type="file"]').click();
};

// Обработка загруженных файлов
const handleFileUpload = (event) => {
	const files = Array.from(event.target.files);
	selectedFiles.value = [...selectedFiles.value, ...files];
};

// Удаление файла из списка
const removeFile = (index) => {
	selectedFiles.value.splice(index, 1);
};

// Функция для начала записи голоса
const startRecording = async () => {
	console.log("Запись началась");
	if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

			// Создаем AudioContext и подключаем анализатор
			audioContext.value = new (window.AudioContext || window.webkitAudioContext)();
			analyser.value = audioContext.value.createAnalyser();
			analyser.value.fftSize = 256;

			const source = audioContext.value.createMediaStreamSource(stream);
			source.connect(analyser.value);

			// Запускаем запись
			mediaRecorder.value = new MediaRecorder(stream);
			recordedAudio.value = [];

			mediaRecorder.value.ondataavailable = (event) => {
				if (event.data.size > 0) {
					recordedAudio.value.push(event.data);
				}
			};

			mediaRecorder.value.onstop = () => {
				stream.getTracks().forEach(track => track.stop());
				if (recordedAudio.value.length > 0) {
					const audioBlob = new Blob(recordedAudio.value, { type: 'audio/webm' });
					audioUrl.value = URL.createObjectURL(audioBlob);
					console.log("Аудио записано:", audioUrl.value);
				}
				audioContext.value.close(); // Останавливаем AudioContext
			};

			mediaRecorder.value.start(100); // Интервал сбора данных
			isRecording.value = true;

			// Запускаем анимацию уровня громкости
			updateAudioLevel();

			window.addEventListener('mouseup', stopRecording);
			window.addEventListener('mouseleave', stopRecording);
		} catch (error) {
			console.error('Ошибка доступа к микрофону:', error);
		}
	} else {
		console.error('Ваш браузер не поддерживает запись аудио.');
	}
};

// Функция для остановки записи голоса
const stopRecording = () => {
	console.log("Запись остановлена");
	if (mediaRecorder.value && isRecording.value) {
		mediaRecorder.value.stop();
		isRecording.value = false;
		isAudioRecorded.value = true; // Показываем плеер только после завершения записи

		window.removeEventListener('mouseup', stopRecording);
		window.removeEventListener('mouseleave', stopRecording);
	}
};

const updateAudioLevel = () => {
	if (!analyser.value) return;

	const dataArray = new Uint8Array(analyser.value.frequencyBinCount);
	const update = () => {
		if (isRecording.value) {
			analyser.value.getByteFrequencyData(dataArray);
			const level = Math.max(...dataArray) / 255; // Нормализуем уровень громкости (0–1)
			audioLevel.value = level;
			requestAnimationFrame(update);
		}
	};
	update();
};

// Очистка записанного аудио
const clearAudio = () => {
	recordedAudio.value = null;
	audioUrl.value = null;
	isAudioRecorded.value = false;
};

// Переключение видимости пикера эмодзи
const toggleEmojiPicker = () => {
	isEmojiPickerVisible.value = !isEmojiPickerVisible.value;
};

// Вставка эмодзи в текстовое поле
const insertEmoji = (emoji) => {
	messageInput.value += emoji;
	isEmojiPickerVisible.value = false;
};

// Подготовка сообщения для отправки
const prepareMessage = () => {
	if (!messageInput.value.trim() && !recordedAudio.value && selectedFiles.value.length === 0) return;

	const messageData = {
		text: messageInput.value.trim(),
		files: selectedFiles.value,
		audio: recordedAudio.value ? audioUrl.value : null,
	};

	// Очищаем поля после подготовки
	messageInput.value = '';
	selectedFiles.value = [];
	clearAudio();
	isAudioRecorded.value = false; // Сбрасываем флаг после отправки

	// Эмитируем событие для отправки данных
	emit('send-message', messageData);
};

onUnmounted(() => {
	if (audioContext.value) {
		audioContext.value.close();
	}
});
</script>

<style scoped>
.chat-window-inputs {
	display: flex;
	flex-direction: column;
	padding: 10px;
	background-color: var(--bg-light);
}

/* Блок для отображения выбранных файлов */
.file-preview {
	margin-bottom: 10px;
	display: flex;
	gap: 10px;
	flex-wrap: wrap;
}

.file-item {
	display: flex;
	align-items: center;
	background-color: #f0f0f0;
	padding: 5px;
	border-radius: 5px;
}

.file-thumbnail img {
	width: 30px;
	height: 30px;
	border-radius: 5px;
}

.file-icon {
	font-size: 20px;
	margin-right: 5px;
}

.remove-file {
	margin-left: 5px;
	color: red;
	cursor: pointer;
}

/* Блок для отображения записанного аудио */
.audio-preview {
    margin-bottom: 10px;
    display: flex;
    align-items: center; /* Выравнивание по вертикали */
    justify-content: space-between; /* Распределяет элементы по краям */
}

/* Плеер */
.audio-preview audio {
    flex: 1; /* Занимает все доступное пространство */
    max-width: 100%; /* Предотвращает переполнение */
}

/* Контейнер для кнопок */
.audio-preview .controls {
    display: flex;
    align-items: center;
}

/* Стили кнопок */
.audio-preview button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 20px;
    color: var(--primary-color);
    margin-left: 5px; /* Отступ между кнопками */
}

.remove-audio {
	color: red;
	cursor: pointer;
}

/* Блок для отображения эмодзи */
.emoji-picker {
	margin-bottom: 10px;
	display: grid;
	grid-template-columns: repeat(5, 1fr);
	gap: 5px;
}

.emoji-item {
	font-size: 20px;
	text-align: center;
	cursor: pointer;
}

/* Поле ввода текста */
.input-container {
	position: relative;
	width: 100%;
}

.input-container input[type='text'] {
	width: 100%;
	padding: 10px 50px 10px 40px;
	border: 1px solid var(--primary-color);
	border-radius: 20px;
	font-size: 16px;
	height: 40px; /* Установим фиксированную высоту */
}

.input-container button {
	position: absolute;
	background: none;
	border: none;
	cursor: pointer;
	font-size: 20px;
	color: var(--primary-color);
}

.emoji-button {
	left: 10px;
	top: 50%;
	transform: translateY(-50%);
}

.attach-button {
	right: 50px;
	top: 50%;
	transform: translateY(-50%);
}

.input-container .record-button,
.input-container .send-button {
	position: absolute;
	right: 10px;
	top: 50%;
	transform: translateY(-50%);
}

/* Область записи (индикатор + кнопка) */
.recording-area {
	display: flex;
	align-items: center;
	justify-content: space-between;
	height: 40px; /* Соответствует высоте текстового поля */
}

/* Индикатор записи голоса */
.recording-indicator {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: center;
}

/* Кнопка записи */
.record-button {
	background: none;
	border: none;
	cursor: pointer;
	font-size: 20px;
	color: var(--primary-color);
	margin-left: 10px; /* Отступ между индикатором и кнопкой */
}

/* Анимация уровня громкости */
.audio-level-bar {
	width: 100%;
	height: 10px;
	background-color: #ddd;
	border-radius: 5px;
	overflow: hidden;
}

.audio-level-fill {
	height: 100%;
	background-color: var(--primary-color);
	transition: width 0.1s ease;
}
</style>