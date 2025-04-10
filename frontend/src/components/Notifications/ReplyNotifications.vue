<template>
	<div class="reply-notifications">
		<button @click="toggleNotifications">
			<i class="icon-bell"></i>
			<span v-if="hasUnreadReplies" class="badge">{{ unreadReplies.length }}</span>
		</button>

		<div v-if="shouldShowNotifications" class="dropdown">
			<div v-for="reply in unreadReplies" :key="reply.uid" class="notification-item" @click="openChat(reply)">
				<img :src="reply.sender?.avatar || '/default-avatar.png'" class="avatar">
				<div class="content">
					<strong>{{ reply.sender?.username || 'User' }}</strong>
					<p>{{ reply.content }}</p>
					<small>{{ formatDate(reply.timestamp) }}</small>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';

const store = useStore();
const router = useRouter();
const showNotifications = ref(false);
const newNotificationArrived = ref(false);

// Геттеры
const unreadReplies = computed(() => store.getters['chat/unreadReplies'] || []);
const hasUnreadReplies = computed(() => unreadReplies.value.length > 0);

// Автоматически показывать уведомления при их получении
watch(unreadReplies, (newVal, oldVal) => {
	if (newVal.length > oldVal.length) {
		newNotificationArrived.value = true;
		showNotifications.value = true;

		// Автоматически скрыть через 5 секунд
		setTimeout(() => {
			if (newNotificationArrived.value) {
				showNotifications.value = false;
				newNotificationArrived.value = false;
			}
		}, 5000);
	}
});

// Комбинированное условие для отображения
const shouldShowNotifications = computed(() => {
	return showNotifications.value && hasUnreadReplies.value;
});

// Методы
const toggleNotifications = () => {
	showNotifications.value = !showNotifications.value;
	newNotificationArrived.value = false; // Сброс флага при ручном управлении
};

const openChat = (reply) => {
	store.commit('chat/CLEAR_UNREAD_REPLIES');
	router.push(`/`);
	showNotifications.value = false;
};

const formatDate = (timestamp) => {
	return new Date(timestamp).toLocaleTimeString();
};
</script>

<style scoped>
.reply-notifications {
	position: relative;
	display: inline-block;
	position: absolute;
	left: 0;
	top: 10px;
	transform: translateX(100%);
	z-index: 9999;
}

.reply-notifications button {
	background-color: transparent;
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
	right: 0;
	left: 0;
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