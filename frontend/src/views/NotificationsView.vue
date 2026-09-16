<template>
	<main class="notification-shell">
		<header class="notification-hero">
			<div>
				<span class="eyebrow">Личный inbox</span>
				<h1>Напоминания</h1>
				<p>Только выбранные вами активности. PubChat не включает напоминания автоматически и не превращает их в streak или давление «не пропустить».</p>
			</div>
			<button v-if="unread" class="ui-button ui-button--ghost" type="button" :disabled="markingAll" @click="markAll">
				{{ markingAll ? 'Отмечаем…' : `Прочитать все · ${unread}` }}
			</button>
		</header>

		<section v-if="loading" class="state-card" role="status">Синхронизируем напоминания…</section>
		<section v-else-if="errorMessage" class="state-card state-card--error" role="alert">
			<strong>Не удалось загрузить inbox</strong>
			<span>{{ errorMessage }}</span>
			<button class="ui-button" type="button" @click="load">Повторить</button>
		</section>
		<section v-else-if="items.length" class="notification-list" aria-label="Уведомления PubChat">
			<button
				v-for="item in items"
				:key="item.uid"
				type="button"
				class="notification-card"
				:class="{ unread: !item.is_read }"
				@click="openNotification(item)"
			>
				<span class="notification-icon"><i class="fas fa-bell" aria-hidden="true"></i></span>
				<span class="notification-copy">
					<span class="notification-title-row"><strong>{{ item.title }}</strong><span v-if="!item.is_read" class="unread-dot">Новое</span></span>
					<span class="notification-body">{{ item.body }}</span>
					<small>{{ contextLabel(item) }} · {{ formatDate(item.created_at) }}</small>
				</span>
				<i v-if="item.context_space_uid" class="fas fa-chevron-right notification-chevron" aria-hidden="true"></i>
			</button>
		</section>
		<section v-else class="state-card">
			<span class="empty-icon"><i class="far fa-bell" aria-hidden="true"></i></span>
			<strong>Здесь спокойно</strong>
			<span>Включите напоминание у нужной активности в «Жизни пространства». Ничего не включается без вашего выбора.</span>
			<RouterLink class="ui-button" to="/">Найти пространство</RouterLink>
		</section>
	</main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { useStore } from 'vuex';

import NotificationService from '@/API/NotificationService';

const router = useRouter();
const store = useStore();
const loading = ref(true);
const markingAll = ref(false);
const errorMessage = ref('');
const items = ref([]);
const unread = computed(() => store.getters['notifications/unread']);

const load = async () => {
	loading.value = true;
	errorMessage.value = '';
	try {
		await store.dispatch('notifications/sync');
		const response = await NotificationService.list({ limit: 100 });
		items.value = response.data.notifications || [];
		store.dispatch('notifications/setUnread', response.data.unread || 0);
	} catch (error) {
		console.error('Не удалось загрузить notifications:', error);
		errorMessage.value = 'Проверьте соединение и попробуйте ещё раз.';
	} finally {
		loading.value = false;
	}
};

const markAll = async () => {
	markingAll.value = true;
	try {
		await NotificationService.markAllRead();
		items.value = items.value.map((item) => ({ ...item, is_read: true }));
		store.dispatch('notifications/setUnread', 0);
	} catch {
		errorMessage.value = 'Не удалось обновить состояние уведомлений.';
	} finally {
		markingAll.value = false;
	}
};

const openNotification = async (item) => {
	if (!item.is_read) {
		try {
			const response = await NotificationService.markRead(item.uid);
			const index = items.value.findIndex((candidate) => candidate.uid === item.uid);
			if (index >= 0) items.value[index] = response.data.notification;
			store.dispatch('notifications/decrementUnread');
		} catch {
			// Navigation stays useful even if read-state update temporarily fails.
		}
	}
	if (item.context_space_uid) {
		await router.push({ name: 'space-life', params: { uid: item.context_space_uid } });
	}
};

const formatDate = (value) => value
	? new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
	: 'только что';
const contextLabel = (item) => item.occurrence_starts_at
	? `Встреча ${new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(item.occurrence_starts_at))}`
	: 'PubChat';

onMounted(load);
</script>

<style scoped>
.notification-shell { display: grid; gap: var(--ui-space-5); padding-bottom: var(--ui-space-8); }.notification-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--ui-space-6); padding: clamp(1.4rem,4vw,2.4rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: linear-gradient(135deg,var(--ui-surface),var(--ui-primary-soft)); }.notification-hero > div { max-width: 44rem; }.eyebrow { color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }.notification-hero h1 { margin: .3rem 0 0; font-size: clamp(1.8rem,4vw,2.8rem); }.notification-hero p { margin: var(--ui-space-3) 0 0; color: var(--ui-text-muted); line-height: 1.6; }.notification-list { display: grid; gap: var(--ui-space-2); }.notification-card { width: 100%; display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: var(--ui-space-3); padding: var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface); color: var(--ui-text); text-align: left; box-shadow: var(--ui-shadow-sm); cursor: pointer; }.notification-card.unread { border-color: color-mix(in srgb,var(--ui-primary) 28%,var(--ui-border)); background: color-mix(in srgb,var(--ui-primary-soft) 28%,var(--ui-surface)); }.notification-icon { width: 2.8rem; height: 2.8rem; display: grid; place-items: center; border-radius: .9rem; background: var(--ui-primary-soft); color: var(--ui-primary); }.notification-copy { min-width: 0; display: grid; gap: .25rem; }.notification-title-row { display: flex; align-items: center; gap: var(--ui-space-2); flex-wrap: wrap; }.notification-title-row strong { font-size: var(--ui-text-md); }.unread-dot { padding: .15rem .45rem; border-radius: var(--ui-radius-pill); background: var(--ui-primary); color: var(--ui-primary-contrast); font-size: .65rem; font-weight: 800; }.notification-body { color: var(--ui-text-muted); line-height: 1.5; }.notification-copy small { color: var(--ui-text-subtle); }.notification-chevron { color: var(--ui-text-subtle); }.state-card { min-height: 16rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); padding: var(--ui-space-6); border: 1px dashed var(--ui-border); border-radius: var(--ui-radius-xl); color: var(--ui-text-muted); text-align: center; }.state-card strong { color: var(--ui-text); font-size: var(--ui-text-lg); }.state-card span { max-width: 35rem; }.state-card .ui-button { margin-top: var(--ui-space-2); }.state-card--error { border-color: color-mix(in srgb,var(--ui-danger) 35%,var(--ui-border)); }.empty-icon { width: 3.5rem; height: 3.5rem; display: grid; place-items: center; border-radius: 1rem; background: var(--ui-surface-muted); color: var(--ui-text-subtle); font-size: 1.3rem; }
@media (max-width: 680px) { .notification-hero { align-items: stretch; flex-direction: column; }.notification-hero .ui-button { width: 100%; }.notification-card { grid-template-columns: auto 1fr; }.notification-chevron { display: none; } }
</style>
