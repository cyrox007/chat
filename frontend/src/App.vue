<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';

import HeaderComponent from './components/HeaderComponent/index.vue';
import ReplyNotifications from '@/components/Notifications/ReplyNotifications.vue';
import MessageNotifications from './components/Notifications/MessageNotifications.vue';
import PwaInstallPrompt from '@/components/Pwa/PwaInstallPrompt.vue';
import PwaUpdateNotice from '@/components/Pwa/PwaUpdateNotice.vue';

const store = useStore();
const router = useRouter();
const networkOnline = ref(navigator.onLine);
const bootstrapError = ref(false);
let authenticatedBootstrap = null;

const connectionNotice = computed(() => {
	if (!store.getters.isAuth) return null;
	if (!networkOnline.value) {
		return {
			tone: 'warning',
			title: 'Вы офлайн',
			message: 'PubChat сохранит текущий экран и восстановит разговоры, когда сеть вернётся.',
		};
	}

	const roomState = store.getters['chat/getConnectionState'];
	const messengerState = store.getters['messenger/getConnectionState'];
	if (['reconnecting', 'offline'].includes(roomState) || ['reconnecting', 'offline'].includes(messengerState)) {
		return {
			tone: 'info',
			title: 'Восстанавливаем связь',
			message: 'Можно оставаться в приложении — повторное подключение выполняется автоматически.',
		};
	}
	if (bootstrapError.value) {
		return {
			tone: 'danger',
			title: 'Сервис временно недоступен',
			message: 'Интерфейс остаётся доступным. PubChat повторит подключение автоматически.',
		};
	}
	return null;
});

const stopAuthenticatedServices = async () => {
	store.dispatch('notifications/stopPolling');
	store.dispatch('notifications/clear');
	await store.dispatch('messenger/disconnectMessenger');
	await store.dispatch('chat/disconnectSocket');
};

const bootstrapAuthenticatedServices = async () => {
	await store.dispatch('syncIdentity');
	await Promise.all([
		store.dispatch('messenger/connectMessenger'),
		store.dispatch('notifications/sync').catch(() => null),
	]);
	store.dispatch('notifications/startPolling');
	const room = store.getters['chat/getCurrentRoom'];
	if (room?.uid) await store.dispatch('chat/connectSocket', room.uid);
	bootstrapError.value = false;
};

const ensureSessionAndConnect = async () => {
	if (!store.getters.isAuth) return;
	if (authenticatedBootstrap) return authenticatedBootstrap;

	authenticatedBootstrap = bootstrapAuthenticatedServices()
		.catch((error) => {
			if (error.response?.status !== 401) bootstrapError.value = true;
		})
		.finally(() => {
			authenticatedBootstrap = null;
		});

	return authenticatedBootstrap;
};

const handleSessionExpired = async () => {
	await stopAuthenticatedServices();
	await store.dispatch('clearUser');
	if (router.currentRoute.value.name !== 'login') {
		await router.replace({ name: 'login', query: { reason: 'session' } });
	}
};

const handleOffline = () => {
	networkOnline.value = false;
};

const handleOnline = () => {
	networkOnline.value = true;
	bootstrapError.value = false;
	if (!store.getters.isAuth) return;
	store.dispatch('messenger/reconnectIfNeeded');
	store.dispatch('chat/reconnectIfNeeded');
	store.dispatch('notifications/sync').catch(() => null);
};

onMounted(async () => {
	await store.dispatch('initializeUser');
	window.addEventListener('pubchat:session-expired', handleSessionExpired);
	window.addEventListener('offline', handleOffline);
	window.addEventListener('online', handleOnline);
	await ensureSessionAndConnect();
});

onUnmounted(() => {
	store.dispatch('notifications/stopPolling');
	window.removeEventListener('pubchat:session-expired', handleSessionExpired);
	window.removeEventListener('offline', handleOffline);
	window.removeEventListener('online', handleOnline);
});

watch(() => store.getters.isAuth, (isAuthenticated, wasAuthenticated) => {
	if (isAuthenticated && !wasAuthenticated) {
		ensureSessionAndConnect();
	} else if (!isAuthenticated && wasAuthenticated) {
		stopAuthenticatedServices();
	}
});
</script>

<template>
	<div class="app-shell">
		<ReplyNotifications />
		<MessageNotifications />
		<HeaderComponent />
		<PwaInstallPrompt />
		<PwaUpdateNotice />

		<transition name="fade">
			<div
				v-if="connectionNotice"
				class="connection-notice"
				:class="`connection-notice--${connectionNotice.tone}`"
				role="status"
				aria-live="polite"
			>
				<div class="connection-notice__pulse" aria-hidden="true"></div>
				<div class="connection-notice__content">
					<strong>{{ connectionNotice.title }}</strong>
					<span>{{ connectionNotice.message }}</span>
				</div>
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
.connection-notice { position: fixed; top: var(--ui-space-3); left: 50%; z-index: 1000; width: min(calc(100% - 24px), 640px); display: flex; align-items: center; gap: var(--ui-space-3); padding: var(--ui-space-3) var(--ui-space-4); transform: translateX(-50%); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface-raised); box-shadow: var(--ui-shadow-lg); color: var(--ui-text); }
.connection-notice--warning { border-color: color-mix(in srgb, var(--ui-warning) 32%, var(--ui-border)); }
.connection-notice--danger { border-color: color-mix(in srgb, var(--ui-danger) 32%, var(--ui-border)); }
.connection-notice--info { border-color: color-mix(in srgb, var(--ui-info) 32%, var(--ui-border)); }
.connection-notice__pulse { width: 0.625rem; height: 0.625rem; flex: 0 0 auto; border-radius: 50%; background: var(--ui-info); animation: connection-pulse 1.6s ease-in-out infinite; }
.connection-notice--warning .connection-notice__pulse { background: var(--ui-warning); }
.connection-notice--danger .connection-notice__pulse { background: var(--ui-danger); }
.connection-notice__content { min-width: 0; display: grid; gap: 2px; }
.connection-notice__content strong { font-size: var(--ui-text-sm); }
.connection-notice__content span { font-size: var(--ui-text-sm); color: var(--ui-text-muted); }
.fade-enter-active, .fade-leave-active { transition: opacity var(--ui-motion-normal) var(--ui-ease), transform var(--ui-motion-normal) var(--ui-ease); }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translate(-50%, -10px); }
@keyframes connection-pulse { 0%, 100% { opacity: 0.45; transform: scale(0.85); } 50% { opacity: 1; transform: scale(1.15); } }
@media (prefers-reduced-motion: reduce) { .connection-notice__pulse { animation: none; } }
@media (max-width: 720px) {
	.app-shell { padding-bottom: 4.75rem; }
	.app-content { margin-top: 0; }
	.connection-notice { top: var(--ui-space-2); width: calc(100% - 16px); padding: var(--ui-space-3); border-radius: var(--ui-radius-md); }
}
</style>
