<script setup>
import { onMounted, onUnmounted, ref } from 'vue';

const updateReady = ref(false);

const showUpdate = () => {
	updateReady.value = true;
};

const reload = () => {
	window.location.reload();
};

const dismiss = () => {
	updateReady.value = false;
};

onMounted(() => window.addEventListener('pubchat:app-update-ready', showUpdate));
onUnmounted(() => window.removeEventListener('pubchat:app-update-ready', showUpdate));
</script>

<template>
	<div v-if="updateReady" class="update-notice" role="status" aria-live="polite">
		<div>
			<strong>Доступно обновление PubChat</strong>
			<span>Перезагрузите приложение, чтобы использовать новую версию.</span>
		</div>
		<div class="update-notice__actions">
			<button class="ui-button" type="button" @click="reload">Обновить</button>
			<button class="update-notice__dismiss" type="button" aria-label="Скрыть уведомление" @click="dismiss">
				<i class="fas fa-xmark" aria-hidden="true"></i>
			</button>
		</div>
	</div>
</template>

<style scoped>
.update-notice {
	position: fixed;
	left: 50%;
	bottom: var(--ui-space-4);
	z-index: 960;
	width: min(38rem, calc(100vw - 2rem));
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--ui-space-3);
	padding: var(--ui-space-3) var(--ui-space-4);
	transform: translateX(-50%);
	border: 1px solid var(--ui-border);
	border-radius: var(--ui-radius-lg);
	background: var(--ui-surface-raised);
	box-shadow: var(--ui-shadow-lg);
}
.update-notice > div:first-child { min-width: 0; display: grid; gap: .15rem; }
.update-notice strong { font-size: var(--ui-text-sm); }
.update-notice span { color: var(--ui-text-muted); font-size: var(--ui-text-xs); }
.update-notice__actions { display: flex; align-items: center; gap: var(--ui-space-2); }
.update-notice__dismiss { width: 2.25rem; height: 2.25rem; border: 0; border-radius: 50%; background: transparent; color: var(--ui-text-muted); cursor: pointer; }
.update-notice__dismiss:hover { background: var(--ui-surface-muted); }
@media (max-width: 720px) {
	.update-notice { bottom: 5.35rem; align-items: stretch; flex-direction: column; }
	.update-notice__actions { justify-content: flex-end; }
}
</style>
