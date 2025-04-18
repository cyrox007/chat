<template>
	<div class="chat-window-inputs" :class="{ disabled: props.isDisabled }">
		<!-- Блок цитаты (если есть) -->
		<div v-if="replyTo" class="reply-preview">
			<div class="reply-header">
				Ответ на сообщение {{ replyTo.sender.name }}
				<button @click="clearReply" class="cancel-reply">
					<i class="fas fa-times"></i>
				</button>
			</div>
			<div class="reply-content">
				{{ truncate(replyTo.content, 50) }}
			</div>
		</div>

		<!-- Отображение выбранных файлов -->
		<div class="file-preview" v-if="selectedFiles.length > 0">
			<div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
				<span v-if="isImage(file)" class="file-thumbnail">
					<img :src="getThumbnail(file)" alt="Thumbnail" />
				</span>
				<span v-else class="file-icon">
					<i :class="getFileIcon(file.type)"></i>
				</span>
				<span class="file-name">{{ file.name }}</span>
				<button class="remove-file" @click="removeFile(index)">
					<i class="fas fa-times"></i>
				</button>
			</div>
		</div>

		<!-- Индикатор записи голоса или видео -->
		<div v-if="isRecording || isVideoRecording" class="recording-area">
			<div class="recording-indicator">
				{{ isRecording ? 'Запись голоса...' : 'Запись видео...' }}
				<div class="audio-level-bar" v-if="isRecording">
					<div class="audio-level-fill" :style="{ width: `${audioLevel * 100}%` }"></div>
				</div>
			</div>
			<button class="stop-record-button" @click="stopRecordingOrVideo">
				<i class="fas fa-stop"></i>
			</button>
		</div>

		<!-- Поле ввода текста -->
		<div class="input-container" v-if="!isRecording && !isAudioRecorded && !isVideoRecording">
			<input type="text" v-model="messageInput" placeholder="Введите сообщение" @keydown.enter="prepareMessage" :disabled="isDisabled" />
			<button class="emoji-button" @click="toggleEmojiPicker">
				<i class="fas fa-smile"></i>
			</button>
			<button class="attach-button" @click="selectFile">
				<i class="fas fa-paperclip"></i>
			</button>
			<!-- Кнопка записи голоса/видео или отправки -->
			<button class="record-button" @click="toggleRecordingType" @mousedown="startRecording"
				@mouseup="stopRecordingOrVideo" v-if="messageInput.trim() === '' && selectedFiles.length === 0">
				<i :class="isRecordingTypeVoice ? 'fas fa-microphone' : 'fas fa-video'"></i>
			</button>
			<button class="send-button" @click="prepareMessage" v-else>
				<i class="fas fa-paper-plane"></i>
			</button>
		</div>

		<!-- Плеер с кнопкой отправки -->
		<div class="audio-preview" v-if="isAudioRecorded">
			<audio controls :src="voiceUrl"></audio>
			<div class="controls">
				<button class="remove-audio" @click="clearVoice" :disabled="isDisabled">
					<i class="fas fa-times"></i>
				</button>
				<button class="send-button" @click="prepareMessage" :disabled="isDisabled">
					<i class="fas fa-paper-plane"></i>
				</button>
			</div>
		</div>

		<!-- Скрытый элемент для выбора файлов -->
		<input type="file" ref="fileInput" @change="handleFileUpload" multiple style="display: none;"
			accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx" :disabled="isDisabled" />

		<!-- Панель выбора эмодзи -->
		<div v-if="isEmojiPickerVisible" class="emoji-picker-container">
			<Picker :data="emojiIndex" set="twitter" @select="insertEmoji" />
		</div>
		<div v-if="isDisabled" class="mute-notification">
            <p>Вы не можете отправлять сообщения.</p>
        </div>
	</div>
</template>

<script setup>
import { ref, defineProps, defineEmits, defineExpose, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import data from "emoji-mart-vue-fast/data/all.json";
import "emoji-mart-vue-fast/css/emoji-mart.css";
import { Picker, EmojiIndex } from "emoji-mart-vue-fast/src";
import imageCompression from 'browser-image-compression';

const emit = defineEmits(['send-message']);

const props = defineProps({
    replyTo: {
        type: Object,
        default: null,
    },
	isDisabled: {
        type: Boolean,
        default: false,
    }
});

const store = useStore();

// Состояния
const messageInput = ref('');
const isRecording = ref(false);
const isVideoRecording = ref(false);
const recordedVoice = ref(null);
const mediaRecorder = ref(null);
const selectedFiles = ref([]);
const isEmojiPickerVisible = ref(false);
const voiceUrl = ref(null);
const audioContext = ref(null);
const analyser = ref(null);
const audioLevel = ref(0);
const isAudioRecorded = ref(false);
const emojiIndex = new EmojiIndex(data);
const replyTo = ref(null);

// Флаг для переключения между записью голоса и видео
const isRecordingTypeVoice = ref(true);

// Разрешенные типы файлов
const allowedMimeTypes = {
	images: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
	videos: ['video/mp4', 'video/webm', 'video/ogg'],
	audio: ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm'],
	documents: [
		'application/pdf',
		'application/msword',
		'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		'application/vnd.ms-excel',
		'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
	],
};

// Проверка типа файла
const isValidFileType = (file, allowedTypes) => {
	return allowedTypes.some((type) => file.type.startsWith(type));
};

// Проверка размера файла
const isFileSizeValid = (file) => {
	const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
	return file.size <= MAX_FILE_SIZE;
};

// Сжатие изображений
const compressImage = async (file) => {
	const options = {
		maxSizeMB: 1,
		maxWidthOrHeight: 1024,
		useWebWorker: true,
		fileType: 'image/webp',
	};
	try {
		const compressedFile = await imageCompression(file, options);
		return new File([compressedFile], file.name, { type: 'image/webp' });
	} catch (error) {
		console.error('Ошибка сжатия изображения:', error);
		return null;
	}
};

// Получение иконки для файла
const getFileIcon = (fileType) => {
	if (fileType.startsWith('image')) return 'fas fa-file-image';
	if (fileType.startsWith('video')) return 'fas fa-file-video';
	if (fileType.startsWith('audio')) return 'fas fa-file-audio';
	if (fileType.startsWith('application/pdf')) return 'fas fa-file-pdf';
	return 'fas fa-file';
};

// Проверка, является ли файл изображением
const isImage = (file) => {
	return file.type.startsWith('image/');
};

// Получение миниатюры изображения
const getThumbnail = (file) => {
	return URL.createObjectURL(file);
};

// Выбор файла
const selectFile = () => {
	document.querySelector('input[type="file"]').click();
};

// Обработка загруженных файлов
const handleFileUpload = async (event) => {
	const files = Array.from(event.target.files).filter((file) => {
		if (!isValidFileType(file, [...allowedMimeTypes.images, ...allowedMimeTypes.videos, ...allowedMimeTypes.audio, ...allowedMimeTypes.documents])) {
			console.warn(`Файл ${file.name} имеет недопустимый тип.`);
			return false;
		}
		if (!isFileSizeValid(file)) {
			console.warn(`Файл ${file.name} слишком большой.`);
			return false;
		}
		return true;
	});

	// Сжимаем изображения
	const processedFiles = await Promise.all(
		files.map(async (file) => {
			if (allowedMimeTypes.images.includes(file.type)) {
				return await compressImage(file);
			}
			return file;
		})
	);

	selectedFiles.value = [...selectedFiles.value, ...processedFiles.filter((file) => file)];
};

// Удаление файла из списка
const removeFile = (index) => {
	selectedFiles.value.splice(index, 1);
};

// Переключение типа записи (голос/видео)
const toggleRecordingType = () => {
	isRecordingTypeVoice.value = !isRecordingTypeVoice.value;
};

// Запуск записи голоса
const startRecording = async () => {
	if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			audioContext.value = new (window.AudioContext || window.webkitAudioContext)();
			analyser.value = audioContext.value.createAnalyser();
			analyser.value.fftSize = 256;
			const source = audioContext.value.createMediaStreamSource(stream);
			source.connect(analyser.value);

			mediaRecorder.value = new MediaRecorder(stream);
			recordedVoice.value = [];
			mediaRecorder.value.ondataavailable = (event) => {
				if (event.data.size > 0) {
					recordedVoice.value.push(event.data);
				}
			};
			mediaRecorder.value.onstop = () => {
				stream.getTracks().forEach(track => track.stop());
				if (recordedVoice.value.length > 0) {
					const voiceBlob = new Blob(recordedVoice.value, { type: 'audio/webm' });
					voiceUrl.value = URL.createObjectURL(voiceBlob);
					isAudioRecorded.value = true;
				}
				audioContext.value.close();
			};
			mediaRecorder.value.start(100);
			isRecording.value = true;
			updateAudioLevel();
		} catch (error) {
			console.error('Ошибка доступа к микрофону:', error);
		}
	} else {
		console.error('Ваш браузер не поддерживает запись аудио.');
	}
};

// Остановка записи
const stopRecordingOrVideo = () => {
	if (isRecording.value) {
		mediaRecorder.value.stop();
		isRecording.value = false;
	}
	if (isVideoRecording.value) {
		// Логика остановки записи видео
		isVideoRecording.value = false;
	}
};

// Обновление уровня громкости
const updateAudioLevel = () => {
	if (!analyser.value) return;
	const dataArray = new Uint8Array(analyser.value.frequencyBinCount);
	const update = () => {
		if (isRecording.value) {
			analyser.value.getByteFrequencyData(dataArray);
			const level = Math.max(...dataArray) / 255;
			audioLevel.value = level;
			requestAnimationFrame(update);
		}
	};
	update();
};

// Очистка записанного голоса
const clearVoice = () => {
	recordedVoice.value = null;
	voiceUrl.value = null;
	isAudioRecorded.value = false;
};

// Переключение видимости пикера эмодзи
const toggleEmojiPicker = () => {
	isEmojiPickerVisible.value = !isEmojiPickerVisible.value;
};

// Вставка эмодзи в текстовое поле
const insertEmoji = (emoji) => {
	messageInput.value += emoji.native || emoji;
	isEmojiPickerVisible.value = false;
};

// Определение типа контента
const determineContentType = ({ text, files, voice }) => {
	if (voice) {
		return 'voice'; // Голосовое сообщение
	}
	if (files && files.length > 0) {
		// Если есть файлы, определяем их тип
		const firstFile = files[0];
		if (firstFile.type.startsWith('image/')) {
			return 'image';
		} else if (firstFile.type.startsWith('video/')) {
			return 'video';
		} else if (firstFile.type.startsWith('audio/')) {
			return 'audio';
		} else {
			return 'file'; // Документ или другой тип файла
		}
	}
	if (text && text.trim() !== '') {
		return 'text'; // Текстовое сообщение
	}
	return 'unknown'; // Неизвестный тип
};

// Обработчик установки цитаты (вызывается из родителя)
const setReply = (message) => {
	replyTo.value = message;
	focusInput();
};

// Очистка цитаты
const clearReply = () => {
	replyTo.value = null;
};

// Фокусировка на поле ввода
const focusInput = () => {
	document.querySelector('.input-container input')?.focus();
};

const truncate = (text, length) => {
  if (!text) return '';
  return text.length > length ? text.slice(0, length) + '...' : text;
};

defineExpose({
	setReply,
	focusInput
});
const processFiles = async () => {
	if (selectedFiles.value.length === 0) return [];

	return await Promise.all(
		selectedFiles.value.map(async (file) => {
			const base64 = await new Promise((resolve, reject) => {
				const reader = new FileReader();
				reader.onload = () => resolve(reader.result);
				reader.onerror = (error) => reject(error);
				reader.readAsDataURL(file);
			});

			return {
				url: base64,
				name: file.name,
				type: file.type,
				size: file.size
			};
		})
	);
};

const processVoice = async () => {
	if (!recordedVoice.value || recordedVoice.value.length === 0) return null;

	return await new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result);
		reader.onerror = (error) => reject(error);
		reader.readAsDataURL(new Blob(recordedVoice.value, { type: 'audio/webm' }));
	});
};

// Подготовка сообщения для отправки
// Модифицированная функция подготовки сообщения
const prepareMessage = async () => {
	if (props.isDisabled) return;
	if (!messageInput.value.trim() && !recordedVoice.value && selectedFiles.value.length === 0) return;

	const messagePayload = {
		content: messageInput.value.trim() || '',
		content_type: determineContentType({
			text: messageInput.value.trim(),
			files: selectedFiles.value,
			voice: recordedVoice.value,
		}),
		media_metadata: {
			files: await processFiles(),
			voice: await processVoice(),
		},
		reply_to_uid: replyTo.value?.uid // Добавляем UID сообщения, на которое отвечаем
	};

	// Очищаем поля
	messageInput.value = '';
	selectedFiles.value = [];
	clearVoice();
	clearReply();

	emit('send-message', messagePayload);
};

onUnmounted(() => {
	if (audioContext.value) {
		audioContext.value.close();
	}
});
</script>

<style scoped>
.chat-window-inputs {
	position: relative;
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
	margin-left: 10px;
	/* Отступ между индикатором и кнопкой */
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

/* Панель выбора эмодзи */
.emoji-picker-container {
	position: absolute;
	bottom: 75px; /* Выравнивание относительно поля ввода */

	left: 0;
	right: 0;
	width: 338px;
	/* max-height: 300px; */ /* Максимальная высота */
	overflow-y: auto; /* Вертикальная прокрутка */
	background-color: var(--bg-light);
	border: 1px solid var(--primary-color);
	border-radius: 10px;
	z-index: 1000; /* Убедитесь, что панель отображается поверх других элементов */
}
.file-preview .file-item .file-name {
	text-overflow: ellipsis;
	white-space: nowrap;
	overflow: hidden;
	white-space: nowrap;
    max-width: 150px; /* Ограничиваем максимальную ширину */
}
/* Стили для блока цитаты */
.reply-preview {
	background: rgba(var(--primary-color-rgb), 0.1);
	border-left: 3px solid var(--primary-color);
	padding: 8px;
	margin-bottom: 8px;
	border-radius: 0 4px 4px 0;
	position: relative;
}

.reply-header {
	font-size: 0.8em;
	color: var(--primary-color);
	display: flex;
	justify-content: space-between;
}

.reply-content {
	font-size: 0.9em;
	color: #555;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.cancel-reply {
	background: none;
	border: none;
	color: #999;
	cursor: pointer;
}

/* Адаптивные стили */
@media (max-width: 768px) {
	.reply-preview {
		padding: 6px;
		margin-bottom: 6px;
	}
}
.message-composer.disabled {
	opacity: 0.6;
	pointer-events: none;
}

.mute-notification {
	background-color: #ffebee;
	color: #c62828;
	padding: 10px;
	border-radius: 4px;
	margin-top: 10px;
}
</style>