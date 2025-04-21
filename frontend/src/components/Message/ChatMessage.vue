<template>
	<div v-if="safeMessage" :class="['message', messageType, { 'has-reply': safeMessage.reply_to }]">
		<!-- Кнопка "ответить" -->
		<button class="reply-button" @click="handleReply"
			:aria-label="`Ответить на сообщение от ${safeMessage.sender.name}`">
			<i class="fas fa-reply"></i>
		</button>
		<!-- Блок цитируемого сообщения -->
		<div v-if="safeMessage.reply_to" class="reply-preview">
			<div class="reply-header">
				<i class="fas fa-reply"></i>
				{{ safeMessage.reply_to.sender.name }}
			</div>
			<div class="reply-content">
				{{ truncate(safeMessage.reply_to.content, 50) }}
			</div>
		</div>

		<!-- Заголовок сообщения -->
		<div class="message-header">
			<img :src="apiBaseUrl + safeMessage.sender.avatar" alt="Аватар" class="avatar" />
			<div class="user-info">
				<strong>{{ safeMessage.sender.name }}</strong>
				<span class="timestamp">{{ formattedTimestamp }}</span>
			</div>
		</div>

		<!-- Тело сообщения -->
		<div class="message-body">
			<div v-if="safeMessage.content_type === 'text'">
				<!-- Текст -->
				{{ safeMessage.content }}
			</div>

			<div v-else-if="safeMessage.content_type === 'image'" class="image_list">
				<!-- Изображение -->
				<div class="image_item" v-for="(image, index) in safeMessage.media_metadata.files" :key="index">
					<img :src="image.url" alt="Изображение" class="message-image" />
				</div>

				<span v-show="safeMessage.content">{{ safeMessage.content }}</span>
			</div>

			<div v-else-if="safeMessage.content_type === 'video'">
				<!-- Видео -->
				<video controls class="message-video">
					<source :src="safeMessage.media_metadata.files[0].url" type="video/mp4">
					Ваш браузер не поддерживает видео.
				</video>
			</div>

			<div v-else-if="safeMessage.content_type === 'audio'">
				<!-- Аудио -->
				<audio controls class="message-audio">
					<source :src="safeMessage.content" type="audio/mpeg">
					Ваш браузер не поддерживает аудио.
				</audio>
			</div>

			<div v-else-if="safeMessage.content_type === 'file'" class="message-files">
				<!-- Файлы -->
				<!-- Проверка на null или отсутствие files -->
				<div
					v-if="safeMessage.media_metadata && safeMessage.media_metadata.files && safeMessage.media_metadata.files.length > 0">
					<div v-for="(file, index) in safeMessage.media_metadata.files" :key="index" class="file-item">
						<span v-if="isImage(file)" class="file-thumbnail">
							<img :src="apiBaseUrl + file" alt="Thumbnail" />
						</span>
						<span v-else class="file-icon">
							<i :class="getFileIcon(file.name)"></i> <!-- Значок для файлов -->
						</span>
						<a :href="apiBaseUrl + file.url" target="_blank" class="file-link">{{ file.name }}</a>
					</div>
				</div>
				<!-- Если media_metadata отсутствует или files пустой -->
				<div v-else class="no-files-message">
					<i class="fas fa-exclamation-circle"></i> Нет доступных файлов
				</div>
			</div>

			<!-- Неизвестный тип контента -->
			<div v-else>Неизвестный тип сообщения</div>
		</div>

		<!-- Индикатор статуса -->
		<div v-if="safeMessage.status" class="message-status">
			<i v-if="safeMessage.status === 'sending'" class="fas fa-spinner fa-spin status-icon sending"></i>
			<i v-else-if="safeMessage.status === 'sent'" class="fas fa-check status-icon sent"></i>
			<i v-else-if="safeMessage.status === 'error'" class="fas fa-exclamation-circle status-icon error"></i>
		</div>
	</div>

	<!-- Индикатор загрузки -->
	<div v-else class="loading-message">Загрузка сообщения...</div>
</template>

<script setup>
import { defineProps, defineEmits, computed } from 'vue';
import { useStore } from 'vuex';

// Инициализируем хранилище
const store = useStore();

const emit = defineEmits(['reply']);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

// Определяем пропсы
const props = defineProps({
	message: {
		type: Object,
		required: true,
	},
});

const currentUser = computed(() => {
    return store.getters.getUser || {
        uid: null,
        username: 'Неизвестный пользователь',
        avatar: '/images/default-avatar.png',
    };
});

// Проверка, является ли файл изображением
const isImage = (fileUrl) => {
	if (!fileUrl) return false;

	// Проверяем, является ли строка Base64
	const base64Pattern = /^data:image\/(jpeg|jpg|png|gif|webp);base64,/;
	if (base64Pattern.test(fileUrl)) {
		return true;
	}

	// Проверяем, является ли строка URL с расширением изображения
	return /\.(jpeg|jpg|png|gif|webp)$/i.test(fileUrl);
};

const getFileIcon = (fileUrl) => {
	// Проверяем расширение файла
	const extension = fileUrl.split('.').pop().toLowerCase();

	// Возвращаем соответствующий класс или путь к иконке
	if (extension === 'pdf') {
		return 'fas fa-file-pdf'; // Иконка PDF
	} else if (['doc', 'docx'].includes(extension)) {
		return 'fas fa-file-word'; // Иконка Word
	} else if (['xls', 'xlsx'].includes(extension)) {
		return 'fas fa-file-excel'; // Иконка Excel
	} else if (['zip', 'rar', '7z'].includes(extension)) {
		return 'fas fa-file-archive'; // Иконка архива
	} else {
		return 'fas fa-file'; // Иконка по умолчанию
	}
};

// Создаём безопасный объект сообщения с значениями по умолчанию
const safeMessage = computed(() => {
	if (!props.message) {
		return null;
	}

	// Обрабатываем медиа-метаданные
	const mediaMetadata = props.message.media_metadata || {};
	const files = Array.isArray(mediaMetadata.files) ? mediaMetadata.files : [];

	// Обрабатываем отправителя
	const sender = props.message.sender || {};

	// Обрабатываем ответ на сообщение
	let replyTo = null;
	if (props.message.reply_to) {
		replyTo = {
			uid: props.message.reply_to.uid || null,
			content: props.message.reply_to.content || '',
			sender: {
				uid: props.message.reply_to.sender?.uid || null,
				name: props.message.reply_to.sender?.name || 'Неизвестный пользователь'
			}
		};
	}

	return {
		uid: props.message.uid || null,
		frontId: props.message.frontId || props.message.tempId || null,
		content: props.message.content || props.message.text || '', // Поддержка старого и нового формата
		content_type: props.message.content_type || 'text',
		media_metadata: {
			files: files,
		},
		sender: {
			uid: sender.uid || null,
			name: sender.username || sender.name || 'Неизвестный пользователь',
			avatar: sender.avatar || '/images/default-avatar.png',
		},
		room_uid: props.message.room_uid || null,
		created_at: props.message.created_at || new Date().toISOString(),
		status: props.message.status || 'sent',
		reply_to: replyTo, // Добавляем информацию о цитируемом сообщении
		type: props.message.type || 'message' // Добавляем тип сообщения
	};
});

// Форматируем дату для отображения
const formattedTimestamp = computed(() => {
	if (!safeMessage.value) return '';

	let rawDate = safeMessage.value.created_at;
	if (!rawDate.endsWith('Z')) {
		rawDate += 'Z'; // Добавляем суффикс Z, если его нет
	}
	const utcDate = new Date(rawDate);

	return `${utcDate.toLocaleDateString()} ${utcDate.toLocaleTimeString()}`;
});

// Вычисляем тип сообщения
const messageType = computed(() => {
	if (!safeMessage.value) {
		return 'loading'; // Если сообщение еще не загружено
	}
	
	// Проверяем, является ли отправитель текущим пользователем
	const isSender = safeMessage.value.sender.uid === currentUser.value.uid;

	// Возвращаем комбинированный тип сообщения
	return isSender ? `sender ${safeMessage.value.content_type}` : `other-user ${safeMessage.value.content_type}`;
});

// Добавляем обработчик ответа
const handleReply = () => {
	emit('reply', {
		uid: safeMessage.value.uid,
		content: safeMessage.value.content,
		sender: safeMessage.value.sender
	});
};

// Функция для сокращения текста
const truncate = (text, length) => {
	return text?.length > length ? text.slice(0, length) + '...' : text;
};
</script>

<style scoped>
.message {
	position: relative;
	display: flex;
	flex-direction: column;
	max-width: 80%;
	padding: 10px;
	border-radius: 10px;
	margin: 5px 0;
	box-shadow: var(--shadow-light);
}

.message.sender {
	background-color: var(--sent-message-bg); /* Зелёный фон для своих сообщений */
	align-self: flex-end; /* Выравнивание по правому краю */
	color: var(--sent-message-text);
}

.message.other-user {
	background-color: var(--received-message-bg);
	align-self: flex-start; /* Выравнивание по левому краю */
}

.message-header {
	display: flex;
	align-items: center;
	margin-bottom: 5px;
}

.avatar {
	width: 30px;
	height: 30px;
	border-radius: 50%;
	margin-right: 10px;
}

.user-info {
	display: flex;
	flex-direction: column;
}

.timestamp {
	font-size: 12px;
	color: var(--text-light);
}

.message-body {
	margin-top: 5px;
}

.message-image {
	max-width: 100%;
	border-radius: 5px;
}

.message-video,
.message-audio {
	max-width: 100%;
	margin-top: 5px;
}

.loading-message {
	background-color: var(--messenger-input-bg);
	padding: 10px;
	border-radius: 5px;
	text-align: center;
	color: #888;
	font-style: italic;
}
/* Стили для кнопки ответа */
.reply-button {
	position: absolute;
	right: 10px;
	top: 10px;
	background: var(--primary-color-hover);
	border: none;
	border-radius: 50%;
	width: 25px;
	height: 25px;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	opacity: 0;
	transition: opacity 0.2s;
}

.message:hover .reply-button {
	opacity: 1;
}

/* На мобильных устройствах показываем всегда */
@media (max-width: 768px) {
	.reply-button {
		opacity: 1;
	}
}

/* Стили для цитируемого сообщения */
.reply-preview {
	background: rgba(0, 0, 0, 0.05);
	border-left: 3px solid var(--primary-color);
	padding: 5px 10px;
	margin-bottom: 8px;
	border-radius: 0 5px 5px 0;
}

.reply-header {
	font-size: 0.8em;
	color: var(--primary-color);
	display: flex;
	align-items: center;
	gap: 5px;
}

.reply-content {
	font-size: 0.9em;
	color: var(--text-light);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

/* Дополнительный отступ для сообщений с цитатой */
.message.has-reply {
	padding-top: 5px;
}
</style>