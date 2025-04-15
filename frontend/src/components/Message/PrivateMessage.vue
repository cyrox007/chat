<template>
	<div class="message" 
		:class="{ sent: message.isCurrentUser, received: !message.isCurrentUser }"
		:data-message-id="message.uid"
		:data-is-current-user="message.isCurrentUser"
		:data-is-read="message.is_read">
		<!-- Ответ на сообщение -->
		<div v-if="message.reply_to" class="reply-preview">
			<div class="reply-header">
				<i class="fas fa-reply"></i> {{ message.reply_to.sender.name }}
			</div>
			<div class="reply-content">{{ truncate(message.reply_to.content, 50) }}</div>
		</div>

		<!-- Тело сообщения -->
		<div class="message-body">
			<!-- Текст -->
			<div v-if="message.content_type === 'text'">{{ message.content }}</div>

			<!-- Изображения -->
			<div v-else-if="message.content_type === 'image'" class="image-list">
				<div v-for="(image, index) in message.media_metadata.files" :key="index" class="image-item">
					<img :src="image.url" alt="Изображение" class="message-image" />
				</div>
			</div>

			<!-- Видео -->
			<div v-else-if="message.content_type === 'video'" class="video-container">
				<video controls class="message-video">
					<source :src="message.media_metadata.files[0].url" type="video/mp4" />
					Ваш браузер не поддерживает видео.
				</video>
			</div>

			<!-- Аудио -->
			<div v-else-if="message.content_type === 'audio'" class="audio-container">
				<audio controls class="message-audio">
					<source :src="message.media_metadata.files[0].url" type="audio/mpeg" />
					Ваш браузер не поддерживает аудио.
				</audio>
			</div>

			<div v-else-if="message.content_type === 'voice'" class="audio-container">
				<audio controls class="message-audio">
					<source :src="message.media_metadata.voice"/>
				</audio>
			</div>

			<!-- Файлы -->
			<div v-else-if="message.content_type === 'file'" class="file-list">
				<div v-for="(file, index) in message.media_metadata.files" :key="index" class="file-item">
					<span v-if="isImage(file)" class="file-thumbnail">
						<img :src="file.url" alt="Thumbnail" />
					</span>
					<span v-else class="file-icon">
						<i :class="getFileIcon(file.name)"></i>
					</span>
					<a :href="file.url" target="_blank" class="file-link">{{ file.name }}</a>
				</div>
			</div>

			<!-- Неизвестный тип контента -->
			<div v-else>Неизвестный тип сообщения</div>
		</div>

		<!-- Время отправки -->
		<div class="message-time">{{ formatTime(message.created_at) }}</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	message: {
		type: Object,
		required: true,
	},
});

// Усечение текста
const truncate = (text, length) => {
	return text.length > length ? `${text.substring(0, length)}...` : text;
};

// Проверка, является ли файл изображением
const isImage = (file) => {
	const imageExtensions = ["jpg", "jpeg", "png", "gif"];
	const extension = file.name.split(".").pop().toLowerCase();
	return imageExtensions.includes(extension);
};

// Получение иконки для файла
const getFileIcon = (fileName) => {
	const extension = fileName.split(".").pop().toLowerCase();
	switch (extension) {
		case "pdf":
			return "fas fa-file-pdf";
		case "doc":
		case "docx":
			return "fas fa-file-word";
		case "xls":
		case "xlsx":
			return "fas fa-file-excel";
		default:
			return "fas fa-file";
	}
};

// Форматирование времени
const formatTime = (date) => {
	return new Date(date).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
};
</script>

<style scoped>
.message {
	margin-bottom: 15px;
	max-width: 70%;
}

.message.sent {
	margin-left: auto;
	text-align: right;
}

.message.received {
	margin-right: auto;
}

.message-body {
	padding: 10px 15px;
	border-radius: 18px;
	display: inline-block;
	text-align: left;
}

.message.sent .message-body {
	background-color: var(--primary-color);
	color: white;
}

.message.received .message-body {
	background-color: var(--other-user-bg);
	color: var(--text-light);
}

.message-time {
	font-size: 0.7em;
	color: #777;
	margin-top: 5px;
}

@media (prefers-color-scheme: dark) {
	.message-time {
		color: #aaa;
	}
}

.reply-preview {
	margin-bottom: 10px;
	padding: 8px;
	background-color: #e0e0e0;
	border-radius: 8px;
}

.reply-header {
	font-size: 12px;
	color: #555;
}

.reply-content {
	font-size: 14px;
	color: #333;
}

.image-list {
	display: flex;
	gap: 10px;
}

.image-item img {
	max-width: 450px;
	height: auto;
	border-radius: 8px;
}

.video-container video {
	max-width: 100%;
	height: auto;
}

.audio-container audio {
	width: 100%;
}

.file-list .file-item {
	display: flex;
	align-items: center;
	margin-bottom: 5px;
}

.file-icon i {
	font-size: 24px;
	margin-right: 10px;
}

.file-link {
	text-decoration: none;
	color: var(--primary-color);
}

</style>