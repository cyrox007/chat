<template>
	<div class="messenger-container">
		<!-- Левая панель: список диалогов -->
		<div class="conversations-list">
			<div class="search-bar">
				<input type="text" placeholder="Поиск пользователей..." v-model="searchQuery" disabled/>
			</div>
			<div class="conversations">
				<!-- Если диалоги есть -->
				<div v-if="dialogs.length > 0">
					<div v-for="dialog in filteredDialogs" :key="dialog.partner_id" class="conversation-item"
						:class="{ active: isActiveDialog(dialog.partner_id) }"
						@click="openConversation(dialog.partner_id)">
						<div class="user-avatar">
							<img :src="dialog.partner.avatar || '/images/default-avatar.png'" alt="User Avatar" />
						</div>
						<div class="conversation-info">
							<div class="user-name">{{ dialog.partner.username }}</div>
							<div class="last-message">{{ dialog.last_message || 'Нет сообщений' }}</div>
						</div>
						<div class="unread-count" v-if="dialog.unread_count > 0">{{ dialog.unread_count }}</div>
					</div>
				</div>
				<!-- Если диалогов нет -->
				<div v-else class="empty-state">
					<div class="empty-content">
						<!-- <i class="fas fa-comments"></i> -->
						<p>Нет активных диалогов</p>
					</div>
				</div>
			</div>
		</div>
		<!-- Правая панель: текущий диалог -->
		<div class="conversation-view" v-if="activeDialog">
			<div class="conversation-header">
				<div class="back-button" @click="closeConversation" v-if="isMobile">
					<i class="fas fa-arrow-left"></i>
				</div>
				<div class="user-info">
					<img :src="activeDialogUser.avatar || '/images/default-avatar.png'" alt="User Avatar" />
					<span>{{ activeDialogUser.username }}</span>
				</div>
			</div>
			<div class="messages-container" ref="messagesContainer">
                <div v-for="(message, index) in getConversation(activeDialog)" :key="message.uid || index"
                     class="message" :class="{ sent: message.isCurrentUser, received: !message.isCurrentUser }">
                    <div class="message-content" :data-message-id="message.uid">
                        {{ message.content }}
                    </div>
                    <div class="message-time">
                        {{ formatTime(message.created_at) }}
                    </div>
                </div>
            </div>
			<!-- Компонент подготовки сообщений -->
			<MessageComposer ref="messageComposer" @send-message="handleSendMessage" />
		</div>
		<!-- Если диалог не выбран -->
		<div class="empty-state" v-else>
			<div class="empty-content">
				<i class="fas fa-comments"></i>
				<p>Выберите диалог для начала общения</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useStore } from 'vuex';
import MessengerService from '@/API/MessengerService';
import MessageComposer from '@/components/MessageComposer/index.vue';
import DOMPurify from 'dompurify';
import MediaPreview from '@/components/Message/MediaPreview.vue';
import VoiceMessage from '@/components/Message/VoiceMessage.vue';

const store = useStore();
const searchQuery = ref('');
const messagesContainer = ref(null);
const isMobile = ref(window.innerWidth < 768);
const dialogs = ref([]);

// Текущий пользователь
const currentUser = computed(() => {
	const user = store.getters.getUser || {
		uid: null,
		username: 'Неизвестный пользователь',
		avatar: '/images/default-avatar.png',
	};
	return user;
});

// Активный диалог
const activeDialog = computed(() => store.getters['messenger/getActiveDialog']);

// Информация о собеседнике
const activeDialogUser = computed(() => {
	const dialog = dialogs.value.find((d) => d.partner_id === activeDialog.value);
	return dialog?.partner || {};
});

// Загрузка диалогов при монтировании компонента
onMounted(async () => {
	try {
		const response = await MessengerService.getDialogs();
		if (response.data.status === 'ok') {
			dialogs.value = response.data.dialogs;
		}
	} catch (error) {
		console.error('Ошибка при загрузке диалогов:', error);
	}
});

// Фильтрация диалогов по поисковому запросу
const filteredDialogs = computed(() => {
	return dialogs.value.filter((dialog) =>
		dialog.partner.username.toLowerCase().includes(searchQuery.value.toLowerCase())
	);
});

// Открытие диалога
const openConversation = async (userId) => {
	store.dispatch('messenger/setActiveDialog', userId);

	// Загружаем историю переписки
	await store.dispatch('messenger/requestConversation', {
		otherUserId: userId,
		requestId: Date.now().toString(),
	});

	// Инициализируем IntersectionObserver после загрузки сообщений
	nextTick(() => {
		setupIntersectionObserver();
	});
};

// Закрытие диалога
const closeConversation = () => {
	store.dispatch('messenger/setActiveDialog', null);
};

// Проверка активного диалога
const isActiveDialog = (userId) => {
	return activeDialog.value === userId;
};

// Получение истории сообщений для активного диалога
const getConversation = (userId) => {
	return store.getters['messenger/getConversation'](userId);
};

// Отметка сообщения как прочитанного
const markMessageAsRead = async (messageId) => {
	try {
		await store.dispatch('messenger/markMessageAsRead', messageId);
	} catch (error) {
		console.error('Ошибка при отметке сообщения как прочитанного:', error);
	}
};

// Метод для инициализации IntersectionObserver
const setupIntersectionObserver = () => {
	if (!messagesContainer.value) return;

	const options = {
		root: null, // Относительно viewport
		threshold: 0, // Триггер при появлении любого фрагмента элемента
	};

	const observer = new IntersectionObserver((entries) => {
		entries.forEach(entry => {
			if (entry.isIntersecting) {
				const messageId = entry.target.querySelector('.message-content')?.dataset.messageId;
				if (messageId) {
					//console.log('Сообщение видимо:', messageId);
					markMessageAsRead(messageId);
				}
			}
		});
	}, options);

	// Наблюдаем за всеми сообщениями
	Array.from(messagesContainer.value.querySelectorAll('.message')).forEach(messageElement => {
		observer.observe(messageElement);
	});
};

// Обработка отправки сообщения
const handleSendMessage = async (messageData) => {
	// Проверяем, что содержимое сообщения не пустое и активный диалог выбран
	if (!messageData.content.trim() && !messageData.media_metadata?.files?.length && !messageData.media_metadata?.voice) return;

	// Очищаем содержимое текстового поля
	const sanitizedContent = DOMPurify.sanitize(messageData.content);

	// Формируем полезную нагрузку для отправки сообщения
	const messagePayload = {
		frontId: Date.now().toString(), // Временный ID
		content: sanitizedContent || '', // Очищенный текст или пустая строка
		content_type: messageData.content_type, // Тип контента
		media_metadata: messageData.media_metadata, // Медиа-метаданные
		sender: {
			uid: currentUser.value.uid, // UID текущего пользователя
			name: currentUser.value.username, // Имя текущего пользователя
			avatar: currentUser.value.avatar || '/images/default-avatar.png', // Аватар
		},
		receiver_uid: activeDialog.value, // UID получателя
		reply_to_uid: messageData.reply_to_uid, // UID сообщения, на которое отвечаем
		status: 'sending', // Статус отправки
	};

	// Отправляем сообщение через Vuex
	store.dispatch('messenger/sendPrivateMessage', messagePayload);

	// Прокручиваем до конца списка сообщений
	await nextTick();
	scrollToBottom();
};

// Прокрутка до конца списка сообщений
const scrollToBottom = () => {
	if (messagesContainer.value) {
		messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
	}
};

// Автопрокрутка при новых сообщениях
watch(
	() => getConversation(activeDialog.value)?.length,
	() => {
		nextTick(() => {
			scrollToBottom();
			setupIntersectionObserver(); // Обновляем IntersectionObserver при новых сообщениях
		});
	},
	{ deep: true }
);

// Форматирование времени
const formatTime = (date) => {
	return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

onMounted(() => {
	if (messagesContainer.value) {
		const options = {
			root: null, // Относительно viewport
			threshold: 0, // Триггер при появлении любого фрагмента элемента
		};
		const observer = new IntersectionObserver((entries) => {
			entries.forEach(entry => {
				if (entry.isIntersecting) {
					console.log('Сообщение видимо:', entry.target.dataset.messageId);
					markMessageAsRead(entry.target.dataset.messageId);
				}
			});
		}, options);

		// Наблюдаем за всеми сообщениями
		Array.from(messagesContainer.value.querySelectorAll('.message')).forEach(messageElement => {
			console.log('Наблюдаем за сообщением:', messageElement.querySelector('.message-content').dataset.messageId);
			observer.observe(messageElement);
		});
	}
});
</script>

<style scoped>
.messenger-container {
	display: flex;
	height: calc(100vh - 60px);
	background-color: var(--bg-light);
	color: var(--text-light);
}

.conversations-list {
	width: 350px;
	border-right: 1px solid #ddd;
	display: flex;
	flex-direction: column;
	background-color: var(--sidebar-bg-light);
}

.search-bar {
	padding: 15px;
	border-bottom: 1px solid #ddd;
}

.search-bar input {
	width: 100%;
	padding: 8px 15px;
	border-radius: 20px;
	border: 1px solid #ddd;
	outline: none;
}

.conversations {
	flex: 1;
	overflow-y: auto;
}

.conversation-item {
	display: flex;
	padding: 15px;
	cursor: pointer;
	border-bottom: 1px solid #eee;
	align-items: center;
	transition: background-color 0.2s;
}

.conversation-item:hover {
	background-color: rgba(0, 0, 0, 0.05);
}

.conversation-item.active {
	background-color: var(--primary-color);
	color: white;
}

.user-avatar {
	width: 50px;
	height: 50px;
	border-radius: 50%;
	overflow: hidden;
	margin-right: 15px;
}

.user-avatar img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

.conversation-info {
	flex: 1;
	min-width: 0;
}

.user-name {
	font-weight: bold;
	margin-bottom: 5px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.last-message {
	font-size: 0.9em;
	color: #777;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.conversation-item.active .last-message {
	color: rgba(255, 255, 255, 0.8);
}

.unread-count {
	background-color: var(--primary-color);
	color: white;
	border-radius: 50%;
	width: 25px;
	height: 25px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 0.8em;
}

.conversation-item.active .unread-count {
	background-color: white;
	color: var(--primary-color);
}

.conversation-view {
	flex: 1;
	display: flex;
	flex-direction: column;
}

.conversation-header {
	padding: 15px;
	border-bottom: 1px solid #ddd;
	display: flex;
	align-items: center;
	background-color: var(--sidebar-bg-light);
}

.back-button {
	margin-right: 15px;
	cursor: pointer;
	display: none;
}

.user-info {
	display: flex;
	align-items: center;
}

.user-info img {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	margin-right: 10px;
}

.messages-container {
	flex: 1;
	padding: 20px;
	overflow-y: auto;
	background-color: var(--bg-light);
}

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

.message-content {
	padding: 10px 15px;
	border-radius: 18px;
	display: inline-block;
}

.message.sent .message-content {
	background-color: var(--primary-color);
	color: white;
}

.message.received .message-content {
	background-color: var(--other-user-bg);
	color: var(--text-light);
}

.message-time {
	font-size: 0.7em;
	color: #777;
	margin-top: 5px;
}

.empty-state {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	background-color: var(--bg-light);
}

.empty-content {
	text-align: center;
	color: #777;
}

.empty-content i {
	font-size: 3em;
	margin-bottom: 15px;
	color: var(--primary-color);
}

@media (max-width: 768px) {
	.conversations-list {
		width: 100%;
		display: block;
	}

	.conversation-view {
		display: none;
	}

	.conversation-view.active {
		display: flex;
	}

	.back-button {
		display: block;
	}

	.messenger-container.show-conversation .conversations-list {
		display: none;
	}

	.messenger-container.show-conversation .conversation-view {
		display: flex;
	}
}

/* Темная тема */
@media (prefers-color-scheme: dark) {

	.conversations-list,
	.conversation-header {
		background-color: var(--sidebar-bg-dark);
		border-color: #444;
	}

	.search-bar input {
		background-color: #333;
		border-color: #444;
		color: white;
	}

	.conversation-item {
		border-color: #444;
	}

	.conversation-item:hover {
		background-color: rgba(255, 255, 255, 0.05);
	}

	.last-message {
		color: #aaa;
	}

	.message-time {
		color: #aaa;
	}
}

.message.has-media {
	max-width: 85%;
}

.message-media {
	margin-top: 8px;
	display: grid;
	gap: 8px;
}

.media-preview {
	border-radius: 12px;
	overflow: hidden;
	max-width: 100%;
}

.media-preview img {
	max-width: 100%;
	max-height: 300px;
	border-radius: 12px;
	display: block;
}

.file-preview {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	background: rgba(0, 0, 0, 0.05);
	border-radius: 8px;
}

.file-preview i {
	margin-right: 8px;
	font-size: 1.2em;
}

.file-size {
	margin-left: auto;
	font-size: 0.8em;
	opacity: 0.7;
}

.voice-message {
	display: flex;
	align-items: center;
	background: rgba(0, 0, 0, 0.05);
	padding: 8px 12px;
	border-radius: 20px;
}

.voice-message audio {
	flex-grow: 1;
	max-width: 200px;
}

.message-reply {
	border-left: 3px solid var(--primary-color);
	padding-left: 8px;
	margin-bottom: 8px;
	opacity: 0.8;
}

.message-meta {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 4px;
	margin-top: 4px;
	font-size: 0.8em;
}

.message-status {
	margin-left: 4px;
}
</style>