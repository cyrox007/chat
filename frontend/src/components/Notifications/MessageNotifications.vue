<template>
	<div class="message-notifications">
		<button type="button" aria-label="Уведомления о сообщениях" @click="toggleNotifications">
			<i class="icon-bell"></i>
			<span v-if="hasUnreadNotifications" class="badge">{{ unreadNotifications.length }}</span>
		</button>

		<div v-if="shouldShowNotifications" class="dropdown">
			<button
				v-for="notification in unreadNotifications"
				:key="notification.uid"
				type="button"
				class="notification-item"
				@click="openNotification(notification)"
			>
				<img :src="notification.sender?.avatar || '/default-avatar.png'" class="avatar" alt="" />
				<span class="content">
					<strong>{{ notification.sender?.display_name || notification.sender?.username || 'Новое сообщение' }}</strong>
					<span class="notification-text">{{ notification.content }}</span>
					<small>{{ formatDate(notification.timestamp) }}</small>
				</span>
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';

const store = useStore();
const router = useRouter();
const showNotifications = ref(false);

const unreadNotifications = computed(() => store.getters['messenger/getNotifications']);
const hasUnreadNotifications = computed(() => store.getters['messenger/hasUnreadNotifications']);
const shouldShowNotifications = computed(() => showNotifications.value && hasUnreadNotifications.value);

const toggleNotifications = () => {
	showNotifications.value = !showNotifications.value;
};

const openNotification = async (notification) => {
	store.commit('messenger/CLEAR_NOTIFICATIONS');
	showNotifications.value = false;

	if (notification.surface === 'space' && notification.roomUid) {
		await router.push({ name: 'space', params: { uid: notification.roomUid } });
		return;
	}

	if (notification.userId) {
		store.commit('messenger/SET_ACTIVE_DIALOG', notification.userId);
	}
	await router.push({ name: 'messenger' });
};

const formatDate = (timestamp) => new Date(timestamp).toLocaleTimeString([], {
	hour: '2-digit',
	minute: '2-digit',
});
</script>

<style scoped>
.message-notifications {
	position: absolute;
	z-index: 9999;
	display: inline-block;
}

.message-notifications > button {
	background: transparent;
	border: 0;
	color: inherit;
	cursor: pointer;
}

.badge {
	background: var(--ui-primary);
	color: var(--ui-primary-contrast);
	border-radius: 999px;
	padding: 1px 6px;
	font-size: 12px;
	position: absolute;
	top: -5px;
	right: -5px;
}

.dropdown {
	position: absolute;
	top: calc(100% + 8px);
	left: 0;
	width: min(320px, calc(100vw - 24px));
	max-height: 400px;
	overflow-y: auto;
	background: var(--ui-surface-raised);
	border: 1px solid var(--ui-border);
	box-shadow: var(--ui-shadow-lg);
	border-radius: var(--ui-radius-lg);
	z-index: 1000;
}

.notification-item {
	width: 100%;
	padding: 10px;
	border: 0;
	border-bottom: 1px solid var(--ui-border);
	display: flex;
	gap: 10px;
	text-align: left;
	background: transparent;
	color: var(--ui-text);
	cursor: pointer;
}

.notification-item:last-child { border-bottom: 0; }
.notification-item:hover { background: var(--ui-surface-soft); }

.avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	object-fit: cover;
	flex: 0 0 auto;
}

.content {
	min-width: 0;
	flex: 1;
	display: grid;
	gap: 3px;
}

.notification-text {
	color: var(--ui-text-muted);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.content small { color: var(--ui-text-subtle); }
</style>
