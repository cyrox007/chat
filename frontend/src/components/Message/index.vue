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
			<!-- Текст -->
			<div v-if="safeMessage.content_type === 'text'">{{ safeMessage.content }}</div>

			<!-- Изображение -->
			<div v-else-if="safeMessage.content_type === 'image'">
				<img :src="safeMessage.content" alt="Изображение" class="message-image" />
			</div>

			<!-- Видео -->
			<div v-else-if="safeMessage.content_type === 'video'">
				<video controls class="message-video">
					<source :src="safeMessage.content" type="video/mp4">
					Ваш браузер не поддерживает видео.
				</video>
			</div>

			<!-- Аудио -->
			<div v-else-if="safeMessage.content_type === 'audio'">
				<audio controls class="message-audio">
					<source :src="safeMessage.content" type="audio/mpeg">
					Ваш браузер не поддерживает аудио.
				</audio>
			</div>

			<!-- Неизвестный тип контента -->
			<div v-else>Неизвестный тип сообщения</div>
		</div>
	</div>

	<!-- Индикатор загрузки -->
	<div v-else class="loading-message">Загрузка сообщения...</div>
</template>

<script setup>
import { defineProps, computed } from 'vue';
import { useChatStore } from '@/stores/chat'; // Импортируем хранилище

// Инициализируем хранилище
const chatStore = useChatStore();

// Определяем пропсы
const props = defineProps({
	message: {
		type: Object,
		required: true,
	},
});

// Создаём безопасный объект сообщения с значениями по умолчанию
const safeMessage = computed(() => {
	if (!props.message) {
		return null; // Возвращаем null, если сообщение не определено
	}

	return {
		uid: props.message.uid || null,
		content: props.message.content || '', // Текст или ссылка на медиа
		content_type: props.message.content_type || 'text', // Тип контента
		sender: {
			uid: props.message.sender?.uid || null,
			name: props.message.sender?.name || 'Неизвестный пользователь',
			avatar: props.message.sender?.avatar || '/images/default-avatar.png',
		},
		created_at: props.message.created_at || new Date().toISOString(),
	};
});

// Форматируем дату для отображения
const formattedTimestamp = computed(() => {
	const date = new Date(safeMessage.value.created_at);
	return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
});

// Вычисляем тип сообщения
const messageType = computed(() => {
	if (!safeMessage.value) {
		return 'loading'; // Если сообщение еще не загружено
	}

	// Проверяем, является ли отправитель текущим пользователем
	const isSender = safeMessage.value.sender.uid === chatStore.currentUser?.uid;

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