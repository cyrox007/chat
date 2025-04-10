<template>
	<div class="messenger-container">
		<div class="conversations-list">
			<div class="search-bar">
				<input type="text" placeholder="Поиск пользователей..." v-model="searchQuery">
			</div>
			<div class="conversations">
				<div v-for="conversation in filteredConversations" :key="conversation.userId" class="conversation-item"
					:class="{ active: isActiveDialog(conversation.userId) }"
					@click="openConversation(conversation.userId)">
					<div class="user-avatar">
						<img :src="conversation.avatar || '/images/default-avatar.png'" alt="User Avatar">
					</div>
					<div class="conversation-info">
						<div class="user-name">{{ conversation.username }}</div>
						<div class="last-message">{{ getLastMessagePreview(conversation.userId) }}</div>
					</div>
					<div class="unread-count" v-if="getUnreadCount(conversation.userId) > 0">
						{{ getUnreadCount(conversation.userId) }}
					</div>
				</div>
			</div>
		</div>

		<div class="conversation-view" v-if="activeDialog">
			<div class="conversation-header">
				<div class="back-button" @click="closeConversation" v-if="isMobile">
					<i class="fas fa-arrow-left"></i>
				</div>
				<div class="user-info">
					<img :src="activeDialogUser.avatar || '/images/default-avatar.png'" alt="User Avatar">
					<span>{{ activeDialogUser.username }}</span>
				</div>
			</div>

			<div class="messages-container" ref="messagesContainer">
				<div v-for="(message, index) in getConversation(activeDialog)" :key="message.uid || index"
					class="message" :class="{
						'sent': message.isCurrentUser,
						'received': !message.isCurrentUser
					}">
					<div class="message-content">
						{{ message.content }}
					</div>
					<div class="message-time">
						{{ formatTime(message.timestamp) }}
					</div>
				</div>
			</div>

			<div class="message-input">
				<input type="text" v-model="newMessage" placeholder="Введите сообщение..." @keyup.enter="sendMessage">
				<button @click="sendMessage">
					<i class="fas fa-paper-plane"></i>
				</button>
			</div>
		</div>

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

const store = useStore();
const searchQuery = ref('');
const newMessage = ref('');
const messagesContainer = ref(null);
const isMobile = ref(window.innerWidth < 768);

const activeDialog = computed(() => store.getters['messenger/getActiveDialog']);
const conversations = computed(() => store.state.messenger.conversations);
const currentUser = computed(() => store.getters['user/getUser']);

// Пример данных - в реальном приложении нужно заменить на запрос к API
const users = ref([
	{ uid: '1', username: 'Пользователь 1', avatar: '' },
	{ uid: '2', username: 'Пользователь 2', avatar: '' },
	{ uid: '3', username: 'Пользователь 3', avatar: '' },
]);

const filteredConversations = computed(() => {
	return users.value.filter(user =>
		user.username.toLowerCase().includes(searchQuery.value.toLowerCase())
	).map(user => ({
		userId: user.uid,
		username: user.username,
		avatar: user.avatar,
		lastMessage: getLastMessagePreview(user.uid)
	}));
});

const activeDialogUser = computed(() => {
	return users.value.find(user => user.uid === activeDialog.value) || {};
});

function getConversation(userId) {
	return store.getters['messenger/getConversation'](userId);
}

function getUnreadCount(userId) {
	return store.getters['messenger/getUnreadCount'](userId);
}

function getLastMessagePreview(userId) {
	const messages = getConversation(userId);
	if (!messages || messages.length === 0) return 'Нет сообщений';
	const lastMessage = messages[messages.length - 1];
	return lastMessage.content.length > 30
		? lastMessage.content.substring(0, 30) + '...'
		: lastMessage.content;
}

function formatTime(date) {
	return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function isActiveDialog(userId) {
	return activeDialog.value === userId;
}

function openConversation(userId) {
	store.dispatch('messenger/setActiveDialog', userId);
	// Загружаем историю переписки
	store.dispatch('messenger/requestConversation', {
		otherUserId: userId,
		requestId: Date.now().toString()
	});
}

function closeConversation() {
	store.dispatch('messenger/setActiveDialog', null);
}

async function sendMessage() {
	if (!newMessage.value.trim() || !activeDialog.value) return;

	const messageData = {
		content: newMessage.value,
		content_type: 'text',
		receiver_uid: activeDialog.value,
		frontId: Date.now().toString()
	};

	store.dispatch('messenger/sendPrivateMessage', messageData);
	newMessage.value = '';

	await nextTick();
	scrollToBottom();
}

function scrollToBottom() {
	if (messagesContainer.value) {
		messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
	}
}

// Автопрокрутка при новых сообщениях
watch(
	() => getConversation(activeDialog.value)?.length,
	() => nextTick().then(scrollToBottom),
	{ deep: true }
);

onMounted(() => {
	window.addEventListener('resize', () => {
		isMobile.value = window.innerWidth < 768;
	});
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

.message-input {
	padding: 15px;
	border-top: 1px solid #ddd;
	display: flex;
	background-color: var(--sidebar-bg-light);
}

.message-input input {
	flex: 1;
	padding: 10px 15px;
	border-radius: 20px;
	border: 1px solid #ddd;
	outline: none;
	margin-right: 10px;
}

.message-input button {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	border: none;
	background-color: var(--primary-color);
	color: white;
	cursor: pointer;
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
	.conversation-header,
	.message-input {
		background-color: var(--sidebar-bg-dark);
		border-color: #444;
	}

	.search-bar input,
	.message-input input {
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
</style>