<template>
	<div class="message-notifications">
		<button @click="toggleNotifications">
			<i class="icon-bell"></i>
			<span v-if="hasUnreadNotifications" class="badge">{{ unreadNotifications.length }}</span>
		</button>

		<div v-if="shouldShowNotifications" class="dropdown">
			<div v-for="notification in unreadNotifications" :key="notification.uid" class="notification-item"
				@click="openMessenger(notification)">
				<img :src="notification.sender?.avatar || '/default-avatar.png'" class="avatar" />
				<div class="content">
					<strong>{{ notification.sender?.username || 'User' }}</strong>
					<p>{{ notification.content }}</p>
					<small>{{ formatDate(notification.timestamp) }}</small>
				</div>
			</div>
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

// Геттеры
const unreadNotifications = computed(() => store.getters['messenger/getNotifications']);
const hasUnreadNotifications = computed(() => store.getters['messenger/hasUnreadNotifications']);

// Условие для отображения
const shouldShowNotifications = computed(() => showNotifications.value && hasUnreadNotifications.value);

// Методы
const toggleNotifications = () => {
	showNotifications.value = !showNotifications.value;
};

const openMessenger = (notification) => {
	store.commit('messenger/SET_ACTIVE_DIALOG', notification.userId); // Устанавливаем активный диалог
	store.commit('messenger/CLEAR_NOTIFICATIONS'); // Очищаем уведомления
	router.push('/messenger'); // Переходим на страницу мессенджера
	showNotifications.value = false;
};

const formatDate = (timestamp) => {
	return new Date(timestamp).toLocaleTimeString();
};
</script>

<style scoped>
.message-notifications {
	position: absolute;
	z-index: 9999;
	display: inline-block;
}

.message-notifications button {
	background: transparent;
	border: transparent;
}

.badge {
	background: red;
	color: white;
	border-radius: 50%;
	padding: 2px 6px;
	font-size: 12px;
	position: absolute;
	top: -5px;
	right: -5px;
}

.dropdown {
	position: absolute;
	right: 0; left: 0;
	width: 300px;
	max-height: 400px;
	overflow-y: auto;
	background: white;
	box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
	border-radius: 4px;
	z-index: 1000;
}

.notification-item {
	padding: 10px;
	border-bottom: 1px solid #eee;
	display: flex;
	cursor: pointer;
}

.notification-item:hover {
	background: #f5f5f5;
}

.avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	margin-right: 10px;
}

.content {
	flex: 1;
}

.content p {
	margin: 5px 0;
	color: #666;
}

.content small {
	color: #999;
}
</style>