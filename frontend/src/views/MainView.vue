<template>
	<CreateRoomModal
		:isShow="isCreateRoomModalOpen"
		@close="toggleCreateSpaceModal"
		@create-room-complete="loadRooms"
	/>

	<main class="space-shell">
		<LeftSidebar
			:class="{ active: isLeftSidebarActive }"
			:rooms="rooms"
			:userRole="currentUser.global_role"
			:userRating="currentUser.rating"
			@close="closeLeftSidebar"
			@switch-room="switchRoom"
			@open-create-chat-modal="toggleCreateSpaceModal"
		/>

		<section class="space-main">
			<header class="space-header">
				<button
					class="space-header__icon"
					type="button"
					aria-label="Открыть список пространств"
					@click="toggleLeftSidebar"
				>
					<i class="fas fa-layer-group" aria-hidden="true"></i>
				</button>

				<div class="space-header__title">
					<span class="space-header__eyebrow">Пространство</span>
					<div class="space-header__title-row">
						<h1>{{ currentRoom?.name || 'Выберите пространство' }}</h1>
						<span
							v-if="currentRoom?.uid"
							class="connection-chip"
							:class="`connection-chip--${connectionState}`"
							role="status"
						>
							<span class="connection-chip__dot" aria-hidden="true"></span>
							{{ connectionLabel }}
						</span>
					</div>
				</div>

				<button
					class="space-header__icon"
					type="button"
					aria-label="Открыть информацию о пространстве"
					:disabled="!currentRoom?.uid"
					@click="toggleRightSidebar"
				>
					<i class="fas fa-circle-info" aria-hidden="true"></i>
				</button>
			</header>

			<div
				v-if="realtimeNotice && currentRoom?.uid"
				class="space-notice"
				:class="`space-notice--${realtimeNotice.type}`"
				role="status"
			>
				<i class="fas fa-circle-info" aria-hidden="true"></i>
				<span>{{ realtimeNotice.message }}</span>
			</div>

			<div v-if="currentRoom?.uid && !isLoading" class="conversation-area">
				<section id="chat-messages" ref="chatMessages" class="message-stream" aria-label="Сообщения пространства">
					<div v-if="messages.length === 0" class="stream-empty">
						<div class="stream-empty__icon" aria-hidden="true"><i class="fas fa-mug-hot"></i></div>
						<strong>Здесь пока тихо</strong>
						<span>Можно начать разговор без формальностей.</span>
					</div>

					<Message
						v-for="(msg, index) in messages"
						:key="msg.uid || msg.frontId || msg.tempId"
						:message="msg"
						:ref="index === messages.length - 1 ? 'lastMessage' : null"
						@reply="handleMessageReply"
					/>
				</section>

				<div v-if="!isRealtimeReady" class="composer-state" role="status">
					<span v-if="connectionState === 'restricted'">Отправка сообщений недоступна в этом пространстве.</span>
					<span v-else-if="connectionState === 'offline'">Нет сети. Разговор восстановится автоматически.</span>
					<span v-else>Восстанавливаем связь с пространством…</span>
				</div>

				<MessageComposer
					ref="messageComposer"
					@send-message="handleSendMessage"
					:isDisabled="isComposerDisabled"
				/>
			</div>

			<section v-else-if="!isLoading" class="space-placeholder">
				<div class="space-placeholder__art" aria-hidden="true">
					<i class="fas fa-comments"></i>
				</div>
				<h2>Выберите место для разговора</h2>
				<p>Пространства — это небольшие сообщества со своей темой, людьми и атмосферой.</p>
				<button class="ui-button" type="button" @click="toggleLeftSidebar">Посмотреть пространства</button>
			</section>
		</section>

		<Loader :isLoading="isLoading" />

		<RightSidebar
			v-if="currentRoom?.uid && !isLoading"
			:class="{ active: isRightSidebarActive }"
			:roomInfo="currentRoom"
			:users="connectedUsers"
			@close="closeRightSidebar"
			@moderator-changed="handleModeratorChange"
			@user-banned="handleRestrictUser"
		/>
	</main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useStore } from 'vuex';
import { v4 as uuidv4 } from 'uuid';
import DOMPurify from 'dompurify';

import Loader from '@/components/Loader/index.vue';
import LeftSidebar from '@/components/LeftSidebar/index.vue';
import RightSidebar from '@/components/RightSidebar/index.vue';
import Message from '@/components/Message/ChatMessage.vue';
import MessageComposer from '@/components/MessageComposer/index.vue';
import CreateRoomModal from '@/components/MainPageModals/CreateRoomModal.vue';
import RoomsService from '@/API/RoomsService';

const store = useStore();

const isCreateRoomModalOpen = ref(false);
const isLoading = ref(false);
const isLeftSidebarActive = ref(false);
const isRightSidebarActive = ref(false);
const rooms = ref([]);
const messageComposer = ref(null);

const currentRoom = computed(() => store.getters['chat/getCurrentRoom']);
const messages = computed(() => store.getters['chat/getMessages']);
const connectedUsers = computed(() => store.getters['chat/getConnectedUsers']);
const connectionState = computed(() => store.getters['chat/getConnectionState']);
const realtimeNotice = computed(() => store.getters['chat/getRealtimeNotice']);
const isUserMuted = computed(() => store.getters['chat/isUserMuted']);
const isRealtimeReady = computed(() => connectionState.value === 'connected');
const isComposerDisabled = computed(() => isUserMuted.value || !isRealtimeReady.value);

const currentUser = computed(() => store.getters.getUser || {
	uid: null,
	username: 'Неизвестный пользователь',
	avatar: '/images/default-avatar.png',
});

const connectionLabel = computed(() => ({
	idle: 'Не подключено',
	connecting: 'Подключаемся',
	authenticating: 'Проверяем сессию',
	connected: 'В эфире',
	reconnecting: 'Восстанавливаем',
	offline: 'Офлайн',
	restricted: 'Доступ ограничен',
}[connectionState.value] || 'Подключение'));

const loadRooms = async () => {
	try {
		const response = await RoomsService.get_rooms();
		if (response.data.status === 'ok' && response.data.rooms) rooms.value = response.data.rooms;
	} catch (error) {
		console.error('Ошибка загрузки пространств:', error);
	}
};

const handleMessageReply = (message) => {
	messageComposer.value?.setReply(message);
	scrollToBottom();
};

const handleSendMessage = async (messageData) => {
	if (isComposerDisabled.value) return;
	const sanitizedContent = DOMPurify.sanitize(messageData.content || '');
	store.dispatch('chat/sendMessage', {
		frontId: uuidv4(),
		content: sanitizedContent,
		content_type: messageData.content_type,
		media_metadata: messageData.media_metadata,
		sender: {
			uid: currentUser.value.uid,
			name: currentUser.value.display_name || currentUser.value.username,
			avatar: currentUser.value.avatar,
		},
		reply_to_uid: messageData.reply_to_uid,
		status: 'sending',
	});
};

const handleModeratorChange = async ({ userId, isModerator }) => {
	try {
		await store.dispatch('chat/sendModeratorAction', {
			target_user_uid: userId,
			action: isModerator ? 'add_moderator' : 'remove_moderator',
		});
	} catch (error) {
		console.error('Не удалось изменить роль в пространстве:', error);
	}
};

const handleRestrictUser = async (userId) => {
	try {
		await store.dispatch('chat/sendBanAction', {
			target_user_uid: userId,
			reason: 'Нарушение правил пространства',
		});
	} catch (error) {
		console.error('Не удалось ограничить доступ к пространству:', error);
	}
};

const switchRoom = async (room) => {
	isLoading.value = true;
	try {
		const roomData = await RoomsService.get_room(room.uid);
		await store.dispatch('chat/switchRoom', {
			room: roomData.data.room,
			roomId: room.uid,
		});
		isLeftSidebarActive.value = false;
		isRightSidebarActive.value = window.innerWidth >= 1100;
	} catch (error) {
		console.error('Ошибка открытия пространства:', error);
	} finally {
		isLoading.value = false;
	}
};

const toggleLeftSidebar = () => {
	isLeftSidebarActive.value = !isLeftSidebarActive.value;
	if (isLeftSidebarActive.value) isRightSidebarActive.value = false;
};
const closeLeftSidebar = () => { isLeftSidebarActive.value = false; };
const toggleRightSidebar = () => {
	if (!currentRoom.value?.uid) return;
	isRightSidebarActive.value = !isRightSidebarActive.value;
	if (isRightSidebarActive.value && window.innerWidth < 1100) isLeftSidebarActive.value = false;
};
const closeRightSidebar = () => { isRightSidebarActive.value = false; };
const toggleCreateSpaceModal = () => { isCreateRoomModalOpen.value = !isCreateRoomModalOpen.value; };

const scrollToBottom = async () => {
	await nextTick();
	const container = document.getElementById('chat-messages');
	if (container) container.scrollTop = container.scrollHeight;
};

onMounted(async () => {
	await loadRooms();
	if (currentRoom.value?.uid && connectionState.value === 'idle') {
		const savedRoom = rooms.value.find((room) => room.uid === currentRoom.value.uid);
		if (savedRoom) await switchRoom(savedRoom);
	}
});

watch(
	() => messages.value.length,
	async () => scrollToBottom(),
);
</script>

<style scoped>
.space-shell {
	height: calc(100dvh - 4.35rem);
	min-height: 32rem;
	display: flex;
	overflow: hidden;
	border: 1px solid var(--ui-border);
	border-radius: var(--ui-radius-xl);
	background: var(--ui-surface);
	box-shadow: var(--ui-shadow-sm);
}

.space-main {
	min-width: 0;
	flex: 1;
	display: flex;
	flex-direction: column;
	background: var(--ui-bg);
}

.space-header {
	min-height: 4.25rem;
	display: grid;
	grid-template-columns: 2.75rem minmax(0, 1fr) 2.75rem;
	align-items: center;
	gap: var(--ui-space-3);
	padding: var(--ui-space-2) var(--ui-space-4);
	border-bottom: 1px solid var(--ui-border);
	background: color-mix(in srgb, var(--ui-surface) 96%, transparent);
}

.space-header__icon {
	width: 2.65rem;
	height: 2.65rem;
	display: grid;
	place-items: center;
	border: 1px solid var(--ui-border);
	border-radius: var(--ui-radius-md);
	background: var(--ui-surface);
	color: var(--ui-text-muted);
	cursor: pointer;
}
.space-header__icon:hover:not(:disabled) { background: var(--ui-surface-muted); color: var(--ui-text); }
.space-header__icon:disabled { opacity: 0.4; cursor: default; }

.space-header__title { min-width: 0; }
.space-header__eyebrow { display: block; color: var(--ui-text-subtle); font-size: var(--ui-text-xs); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
.space-header__title-row { min-width: 0; display: flex; align-items: center; gap: var(--ui-space-3); }
.space-header h1 { min-width: 0; overflow: hidden; margin: 0.1rem 0 0; text-overflow: ellipsis; white-space: nowrap; font-size: var(--ui-text-lg); }

.connection-chip {
	min-height: 1.75rem;
	display: inline-flex;
	align-items: center;
	gap: var(--ui-space-1);
	padding: 0 var(--ui-space-2);
	border-radius: var(--ui-radius-pill);
	background: var(--ui-surface-muted);
	color: var(--ui-text-muted);
	font-size: var(--ui-text-xs);
	font-weight: 700;
	white-space: nowrap;
}
.connection-chip__dot { width: 0.45rem; height: 0.45rem; border-radius: 50%; background: currentColor; }
.connection-chip--connected { background: var(--ui-success-soft); color: var(--ui-success); }
.connection-chip--reconnecting, .connection-chip--connecting, .connection-chip--authenticating { background: var(--ui-info-soft); color: var(--ui-info); }
.connection-chip--offline { background: var(--ui-warning-soft); color: var(--ui-warning); }
.connection-chip--restricted { background: var(--ui-danger-soft); color: var(--ui-danger); }

.space-notice {
	display: flex;
	align-items: center;
	gap: var(--ui-space-2);
	padding: var(--ui-space-2) var(--ui-space-4);
	border-bottom: 1px solid var(--ui-border);
	background: var(--ui-info-soft);
	color: var(--ui-info);
	font-size: var(--ui-text-sm);
}
.space-notice--warning { background: var(--ui-warning-soft); color: var(--ui-warning); }
.space-notice--error, .space-notice--restricted { background: var(--ui-danger-soft); color: var(--ui-danger); }

.conversation-area { min-height: 0; flex: 1; display: flex; flex-direction: column; }
.message-stream { min-height: 0; flex: 1; overflow-y: auto; padding: var(--ui-space-4) clamp(var(--ui-space-3), 3vw, var(--ui-space-6)); scroll-behavior: smooth; }
.stream-empty { min-height: 100%; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); text-align: center; color: var(--ui-text-muted); }
.stream-empty__icon { width: 3.25rem; height: 3.25rem; display: grid; place-items: center; border-radius: 50%; background: var(--ui-primary-soft); color: var(--ui-primary); font-size: var(--ui-text-xl); }
.stream-empty strong { color: var(--ui-text); font-size: var(--ui-text-lg); }

.composer-state { padding: var(--ui-space-2) var(--ui-space-4); border-top: 1px solid var(--ui-border); background: var(--ui-surface-soft); color: var(--ui-text-muted); font-size: var(--ui-text-xs); text-align: center; }

.space-placeholder { flex: 1; display: grid; place-items: center; align-content: center; gap: var(--ui-space-3); padding: var(--ui-space-8); text-align: center; }
.space-placeholder__art { width: 5rem; height: 5rem; display: grid; place-items: center; border-radius: 1.75rem; background: var(--ui-primary-soft); color: var(--ui-primary); font-size: 2rem; transform: rotate(-4deg); }
.space-placeholder h2 { margin: var(--ui-space-2) 0 0; font-size: var(--ui-text-xl); }
.space-placeholder p { width: min(100%, 30rem); margin: 0; color: var(--ui-text-muted); }
.space-placeholder .ui-button { margin-top: var(--ui-space-2); }

@media (max-width: 991px) {
	.space-shell { height: calc(100dvh - 8.4rem); border-radius: var(--ui-radius-lg); }
	.space-header { padding-inline: var(--ui-space-3); }
}

@media (max-width: 560px) {
	.space-shell { margin-inline: calc(var(--ui-space-3) * -1); border-right: 0; border-left: 0; border-radius: 0; }
	.space-header__eyebrow { display: none; }
	.space-header__title-row { gap: var(--ui-space-2); }
	.space-header h1 { font-size: var(--ui-text-md); }
	.connection-chip { max-width: 7.5rem; overflow: hidden; text-overflow: ellipsis; }
	.message-stream { padding-inline: var(--ui-space-3); }
}
</style>
