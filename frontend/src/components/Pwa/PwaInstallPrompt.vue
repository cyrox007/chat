<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';

const installEvent = ref(null);
const dismissed = ref(false);
const installed = ref(false);

const isStandalone = () => (
	window.matchMedia?.('(display-mode: standalone)').matches
	|| window.navigator.standalone === true
);

const canInstall = computed(() => (
	Boolean(installEvent.value)
	&& !dismissed.value
	&& !installed.value
	&& !isStandalone()
));

const handleBeforeInstall = (event) => {
	event.preventDefault();
	if (sessionStorage.getItem('pubchat:pwa-install-dismissed') === '1') return;
	installEvent.value = event;
};

const handleInstalled = () => {
	installed.value = true;
	installEvent.value = null;
};

const install = async () => {
	const event = installEvent.value;
	if (!event) return;

	await event.prompt();
	const choice = await event.userChoice;
	installEvent.value = null;
	if (choice?.outcome === 'accepted') installed.value = true;
};

const dismiss = () => {
	dismissed.value = true;
	sessionStorage.setItem('pubchat:pwa-install-dismissed', '1');
};

onMounted(() => {
	window.addEventListener('beforeinstallprompt', handleBeforeInstall);
	window.addEventListener('appinstalled', handleInstalled);
});

onUnmounted(() => {
	window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
	window.removeEventListener('appinstalled', handleInstalled);
});
</script>

<template>
	<aside v-if="canInstall" class="install-prompt" aria-label="Установка PubChat">
		<div class="install-prompt__icon" aria-hidden="true"><i class="fas fa-mobile-screen-button"></i></div>
		<div class="install-prompt__copy">
			<strong>PubChat можно установить</strong>
			<span>Откроется как отдельное приложение, без лишней вкладки браузера.</span>
		</div>
		<div class="install-prompt__actions">
			<button class="ui-button" type="button" @click="install">Установить</button>
			<button class="ui-button ui-button--ghost" type="button" @click="dismiss">Не сейчас</button>
		</div>
	</aside>
</template>

<style scoped>
.install-prompt {
	position: fixed;
	right: var(--ui-space-4);
	bottom: var(--ui-space-4);
	z-index: 950;
	width: min(26rem, calc(100vw - 2rem));
	display: grid;
	grid-template-columns: auto 1fr;
	gap: var(--ui-space-3);
	padding: var(--ui-space-4);
	border: 1px solid var(--ui-border);
	border-radius: var(--ui-radius-lg);
	background: var(--ui-surface-raised);
	box-shadow: var(--ui-shadow-lg);
}
.install-prompt__icon {
	width: 2.6rem;
	height: 2.6rem;
	display: grid;
	place-items: center;
	border-radius: var(--ui-radius-md);
	background: var(--ui-primary-soft);
	color: var(--ui-primary);
}
.install-prompt__copy { min-width: 0; display: grid; gap: .2rem; }
.install-prompt__copy strong { font-size: var(--ui-text-sm); }
.install-prompt__copy span { color: var(--ui-text-muted); font-size: var(--ui-text-xs); line-height: 1.45; }
.install-prompt__actions {
	grid-column: 1 / -1;
	display: flex;
	justify-content: flex-end;
	gap: var(--ui-space-2);
}
.ui-button--ghost { border: 1px solid var(--ui-border); background: transparent; color: var(--ui-text-muted); }
@media (max-width: 720px) {
	.install-prompt { right: .6rem; bottom: 5.35rem; width: calc(100vw - 1.2rem); }
	.install-prompt__actions { display: grid; grid-template-columns: 1fr 1fr; }
}
</style>
