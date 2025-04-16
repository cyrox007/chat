<template>
	<div class="user-status">
		<span :class="statusClass">{{ statusText }}</span>
	</div>
</template>

<script setup>
import { computed } from 'vue';
import { useStore } from 'vuex';

const props = defineProps({
	userId: {
		type: String,
		required: true,
	},
});

const store = useStore();

// Получаем статус пользователя
const userStatus = computed(() => store.getters['getUserStatus'](props.userId));

// Текст статуса
const statusText = computed(() => {
	if (!userStatus.value?.last_online) return 'Никогда не был онлайн';

	const lastOnline = new Date(userStatus.value.last_online + 'Z'); // Преобразуем строку в объект Date с учетом UTC
	const now = new Date();
	const diffInSeconds = (now - lastOnline) / 1000; // Разница в секундах
	const diffInMinutes = diffInSeconds / 60; // Разница в минутах
	const diffInHours = diffInMinutes / 60; // Разница в часах
	const diffInDays = diffInHours / 24; // Разница в днях

	// Если пользователь был активен менее 30 секунд назад, считаем его онлайн
	if (diffInSeconds <= 30) {
		return 'Онлайн';
	}

	// Если пользователь был активен менее минуты назад
	if (diffInMinutes < 1) {
		return 'Был несколько секунд назад';
	}

	// Если пользователь был активен менее часа назад
	if (diffInMinutes < 60) {
		const minutes = Math.floor(diffInMinutes);
		return `Был ${minutes} ${minutes === 1 ? 'минуту' : minutes < 5 ? 'минуты' : 'минут'} назад`;
	}

	// Если пользователь был активен менее суток назад
	if (diffInHours < 24) {
		const hours = Math.floor(diffInHours);
		return `Был ${hours} ${hours === 1 ? 'час' : hours < 5 ? 'часа' : 'часов'} назад`;
	}

	// Если пользователь был активен вчера
	if (diffInDays < 2) {
		return 'Был вчера';
	}

	// Если пользователь был активен более двух дней назад, но меньше недели
	if (diffInDays < 7) {
		const days = Math.floor(diffInDays);
		return `Был ${days} ${days === 1 ? 'день' : days < 5 ? 'дня' : 'дней'} назад`;
	}

	// Если пользователь был активен более недели назад, выводим дату
	const options = { year: 'numeric', month: 'long', day: 'numeric' };
	return `Был ${lastOnline.toLocaleDateString('ru-RU', options)}`;
});

// Класс для статуса
const statusClass = computed(() => {
	return statusText.value === 'Онлайн' ? 'online' : 'offline';
});
</script>

<style scoped>
.online {
	color: green;
}

.offline {
	color: grey;
}
</style>