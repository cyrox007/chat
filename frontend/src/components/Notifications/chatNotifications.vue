<script setup>
import { computed } from 'vue';
import { useStore } from 'vuex';

const store = useStore();
const notifications = computed(() => store.getters['chat/getNotifications']);

const clearNotifications = () => {
	store.dispatch('chat/clearNotifications');
};
</script>

<template>
	<div class="notifications">
		<div v-for="(note, index) in notifications" :key="index" @click="clearNotifications">
			Новое сообщение от {{ note.sender.name }}: {{ note.content }}
		</div>
	</div>
</template>