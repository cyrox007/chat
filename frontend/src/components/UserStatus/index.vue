<template>
	<div class="user-status">
		<span :class="statusClass">{{ statusText }}</span>
	</div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue';
import { useStore } from 'vuex';

const props = defineProps({
	userId: {
		type: String,
		required: true,
	},
});

const store = useStore();

// Подписываемся на обновления статуса при монтировании
onMounted(() => {
	store.dispatch('messenger/subscribeToStatuses', [props.userId]);
});

// Отписываемся при размонтировании
onUnmounted(() => {
	store.dispatch('messenger/unsubscribeFromStatuses', [props.userId]);
});

// Получаем онлайн-статус из хранилища
const isOnline = computed(() => store.getters['messenger/isUserOnline'](props.userId));

// Текст статуса
const statusText = computed(() => {
	return isOnline.value ? 'Онлайн' : 'Офлайн';
});

// Класс для статуса
const statusClass = computed(() => {
	return isOnline.value ? 'online' : 'offline';
});
</script>

<style scoped>
.online {
	color: var(--online-color, green);
}

.offline {
	color: var(--offline-color, grey);
}
</style>