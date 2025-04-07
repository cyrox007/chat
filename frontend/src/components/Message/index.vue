<template>
	<div v-if="safeMessage" :class="['message', messageType]">
		<!-- Заголовок сообщения -->
		<div class="message-header">
			<img :src="safeMessage.sender.avatar" alt="Аватар" class="avatar" />
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
					<source :src="safeMessage.content" type="video/mp4">
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
							<img :src="file" alt="Thumbnail" />
						</span>
						<span v-else class="file-icon">
							<i :class="getFileIcon(file.name)"></i> <!-- Значок для файлов -->
						</span>
						<a :href="file.url" target="_blank" class="file-link">{{ file.name }}</a>
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
import { defineProps, computed } from 'vue';
import { useStore } from 'vuex';

// Инициализируем хранилище
const store = useStore();

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

// Извлечение имени файла из URL
const getFileName = (fileUrl) => {
	return fileUrl.split('/').pop();
}

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
		return null; // Возвращаем null, если сообщение не определено
	}

	const mediaMetadata = props.message.media_metadata || {};
	const files = Array.isArray(mediaMetadata.files) ? mediaMetadata.files : [];

	return {
		uid: props.message.uid || null,
		frontId: props.message.tempId,
		content: props.message.content || '', // Текст или ссылка на медиа
		content_type: props.message.content_type || 'text', // Тип контента
		media_metadata: {
			files: files, // Убедимся, что это всегда массив
		},
		sender: {
			uid: props.message.sender?.uid || null,
			name: props.message.sender?.name || 'Неизвестный пользователь',
			avatar: props.message.sender?.avatar || '/images/default-avatar.png',
		},
		created_at: props.message.created_at || new Date().toISOString(),
		status: props.message.status || 'sent', // Статус: отправлено по умолчанию
	};
});

// Форматируем дату для отображения
const formattedTimestamp = computed(() => {
	if (!safeMessage.value) return '';
	const date = new Date(safeMessage.value.created_at);
	return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
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
</script>

<style scoped>
.message {
	display: flex;
	flex-direction: column;
	max-width: 80%;
	padding: 10px;
	border-radius: 10px;
	margin: 5px 0;
	box-shadow: 0 0 13px  rgba(219, 219, 219, 0.76);
}

.message.sender {
	background-color: #dcf8c6;
	/* Зелёный фон для своих сообщений */
	align-self: flex-end;
	/* Выравнивание по правому краю */
}

.message.other-user {
	background-color: #f1f1f1;
	/* Серый фон для чужих сообщений */
	align-self: flex-start;
	/* Выравнивание по левому краю */
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
	color: #888;
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
	background-color: #f5f5f5;
	padding: 10px;
	border-radius: 5px;
	text-align: center;
	color: #888;
	font-style: italic;
}
</style>