<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';

import HeaderComponent from './components/HeaderComponent/index.vue';
import ReplyNotifications from '@/components/Notifications/ReplyNotifications.vue';
import MessageNotifications from './components/Notifications/MessageNotifications.vue';

const store = useStore();
const router = useRouter();
const showErrorNotification = ref(false);

const ensureValidTokenAndConnect = async () => {
	if (!store.getters['isAuth']) return;
	try {
		if (store.getters['chat/getCurrentRoom']) {
			const roomId = store.getters['chat/getCurrentRoom'].uid;
			await store.dispatch('chat/connectSocket', roomId);
		}
		await store.dispatch('messenger/connectMessenger');
		showErrorNotification.value = false;
	} catch (error) {
		if (error.response && [500, 502, 503, 504].includes(error.response.status)) {
			showErrorNotification.value = true;
		} else if (!error.response) {
			showErrorNotification.value = true;
		}
	}
};

const handleSessionExpired = async () => {
	await store.dispatch('clearUser');
	if (router.currentRoute.value.name !== 'login') {
		await router.replace({ name: 'login', query: { reason: 'session' } });
	}
};

onMounted(async () => {
	window.addEventListener('pubchat:session-expired', handleSessionExpired);
	await ensureValidTokenAndConnect();
});

onUnmounted(() => {
	window.removeEventListener('pubchat:session-expired', handleSessionExpired);
});

watch(() => store.getters['isAuth'], (isAuthenticated) => {
	if (isAuthenticated) {
		ensureValidTokenAndConnect();
	} else {
		store.dispatch('messenger/disconnectMessenger');
	}
});
</script>

<template>
	<div class="app-shell">
		<ReplyNotifications />
		<MessageNotifications />
		<HeaderComponent />

		<transition name="fade">
			<div v-if="showErrorNotification" class="connection-notice" role="status" aria-live="polite">
				<div class="connection-notice__content">
					<strong>Связь с PubChat потеряна</strong>
					<span>Можно продолжать просмотр. Подключение восстановится, когда сеть вернётся.</span>
				</div>
				<button type="button" class="connection-notice__close" aria-label="Закрыть уведомление" @click="showErrorNotification = false">×</button>
			</div>
		</transition>

		<main class="container app-content">
			<RouterView />
		</main>
	</div>
</template>

<style scoped>
.app-shell { min-height: 100dvh; }
.app-content { margin-top: var(--ui-space-2); }
.connection-notice { position: fixed; top: var(--ui-space-3); left: 50%; z-index: 1000; width: min(calc(100% - 24px), 620px); display: flex; align-items: flex-start; gap: var(--ui-space-3); padding: var(--ui-space-3) var(--ui-space-4); transform: translateX(-50%); border: 1px solid color-mix(in srgb, var(--ui-danger) 28%, var(--ui-border)); border-radius: var(--ui-radius-lg); background: var(--ui-surface-raised); box-shadow: var(--ui-shadow-lg); color: var(--ui-text); }
.connection-notice__content { min-width: 0; display: grid; gap: 2px; flex: 1; }
.connection-notice__content strong { font-size: var(--ui-text-sm); color: var(--ui-danger); }
.connection-notice__content span { font-size: var(--ui-text-sm); color: var(--ui-text-muted); }
.connection-notice__close { width: 32px; height: 32px; display: inline-grid; place-items: center; flex: 0 0 auto; padding: 0; border: 0; border-radius: var(--ui-radius-md); background: transparent; color: var(--ui-text-muted); font-size: 1.35rem; line-height: 1; cursor: pointer; }
.connection-notice__close:hover { background: var(--ui-surface-muted); color: var(--ui-text); }
.fade-enter-active, .fade-leave-active { transition: opacity var(--ui-motion-normal) var(--ui-ease), transform var(--ui-motion-normal) var(--ui-ease); }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translate(-50%, -10px); }
@media (max-width: 720px) {
	.app-shell { padding-bottom: 4.75rem; }
	.app-content { margin-top: 0; }
	.connection-notice { top: var(--ui-space-2); width: calc(100% - 16px); padding: var(--ui-space-3); border-radius: var(--ui-radius-md); }
}
</style>
