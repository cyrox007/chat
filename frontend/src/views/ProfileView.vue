<template>
	<div class="user-profile">
		<h1>Профиль пользователя</h1>
		<p><strong>Имя:</strong> {{ user?.username }}</p>
		<p><strong>Email:</strong> {{ user?.email }}</p>
		<p><strong>Рейтинг:</strong> {{ user?.rating }}</p>
		<p><strong>Страна:</strong> {{ user?.country }}</p>
		<p><strong>Город:</strong> {{ user?.city }}</p>
		<p><strong>Биография:</strong> {{ user?.bio || 'Нет информации' }}</p>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import UsersServices from '@/API/UsersService';

const route = useRoute();
const user = ref(null);

onMounted(async () => {
	const uid = route.params.uid;
	try {
		const response = await UsersServices.get_user_by_uid(uid);
		if (response.data.status === 'ok') {
			user.value = response.data.user;
		}
	} catch (error) {
		console.error('Ошибка при загрузке профиля пользователя:', error);
	}
});
</script>

<style scoped>
.user-profile {
	padding: 20px;
}
</style>