<template>
	<aside class="chat-sidebar-right" :class="{ active: isActive }">
		<!-- Кнопка закрытия -->
		<button class="close-sidebar" aria-label="Закрыть сайдбар" @click="closeSidebar">
			<i class="fas fa-arrow-right"></i>
		</button>

		<!-- Информация о комнате -->
		<div class="chat-sidebar-info">
			<!-- <h3>Информация о комнате</h3> -->
			<h3 style="text-align: center; margin-bottom: 10px;"><!-- <strong>Название:</strong> --> {{ roomInfo.name }}
			</h3>
			<p><strong>Описание:</strong> {{ roomInfo.description || 'Нет описания' }}</p>
			<p><strong>Страна:</strong> {{ roomInfo.country }}</p>
			<p><strong>Регион:</strong> {{ roomInfo.region }}</p>
			<p><strong>Теги:</strong> {{ roomInfo.tags }}</p>
			<p><strong>Дата создания:</strong> {{ formatDate(roomInfo.created_at) }}</p>
			<p><strong>Владелец:</strong>
				<router-link class="sidebar-link" v-if="owner" :to="`/profile/${owner.uid}`">{{ owner.username }}</router-link>
				<span v-else>Неизвестно</span>
			</p>
			<div class="rating-visualization">
				<h4>Рейтинг комнаты: {{ roomInfo.rating }}</h4>
				<div v-if="roomInfo.rating > 0">
					<EnergyGrid :rating="roomInfo.rating" />
				</div>
				<p v-else>У комнаты пока нет рейтинга.</p>
			</div>
		</div>

		<!-- Список пользователей -->
		<div class="chat-sidebar-users">
			<!-- <h3>Пользователи</h3> -->
			<div class="chat-sidebar-users-list" v-if="users.length > 0">
				<router-link v-for="user in users" :to="`/profile/${user.uid}`" class="username">
					<div :key="user.uid" class="chat-sidebar-users-item" :data-user-id="user.uid">
						<img :src="user.avatar" alt="Avatar" class="user-avatar">
						{{ user.username }}
					</div>
				</router-link>
			</div>
			<p v-else>Нет подключенных пользователей</p>
		</div>
	</aside>
</template>

<script setup>
import { defineProps, defineEmits, ref, onMounted } from 'vue';
import EnergyGrid from '@/components/EnergyGrid/index.vue'; // Компонент для визуализации рейтинга
import UsersServices from '@/API/UsersService';
import { useRouter } from 'vue-router'; // Импортируем роутер

// Определяем пропсы
const props = defineProps({
	isActive: {
		type: Boolean,
		default: false,
	},
	roomInfo: {
		type: Object,
		default: () => ({}),
	},
	users: {
		type: Array,
		default: () => [],
	},
});

// Определяем эмиты
const emit = defineEmits(['close']);

// Хранилище для данных владельца комнаты
const owner = ref(null);

// Функция для закрытия сайдбара
const closeSidebar = () => {
	emit('close');
};

// Форматирование даты
const formatDate = (dateString) => {
	const date = new Date(dateString);
	return date.toLocaleDateString();
};

// Получение данных владельца комнаты
onMounted(async () => {
	if (props.roomInfo.owner_uid) {
		try {
			const response = await UsersServices.get_user_by_uid(props.roomInfo.owner_uid);
			if (response.data.status === 'ok') {
				owner.value = response.data.user;
			}
		} catch (error) {
			console.error('Ошибка при получении данных владельца:', error);
		}
	}
});
</script>

<style scoped>
.chat-sidebar-right {
	position: relative;
	height: 100%;
	min-width: 300px;
	width: 300px;
	display: flex;
	flex-direction: column;
	padding: 10px;
	background-color: var(--sidebar-bg-light);
	transition: transform 0.3s ease-in-out, opacity 0.3s ease-in-out;
}

@media screen and (max-width: 991px) {
	.chat-sidebar-right {
		position: fixed;
		right: 0;
		transform: translateX(120%);
	}
	.chat-sidebar-right.active {
		transform: translateX(0%);
	}
}

@media screen and (max-width: 991px) {
	.chat-sidebar-right {
		height: calc(100% - (50px + 8px));
	}
}

.close-sidebar {
	cursor: pointer;
	position: absolute;
	top: 15px;
	left: -18px;
	background: none;
	border: none;
	display: none;
	background-color: #ccc;
	border-radius: 100%;
	padding: 5px;
	width: 30px;
	height: 30px;
}

@media screen and (max-width: 991px) {
	.close-sidebar {
		display: block;
	}
}

.chat-sidebar-info {
	padding: 20px 10px;
	border-bottom: 1px solid #ddd;
}

.sidebar-link {
	text-decoration: none;
	color: var(--text-light);
	margin-left: 5px;
	transition: text-decoration .15s ease-in;
}

.sidebar-link:hover {
	text-decoration: underline;
}

.chat-sidebar-users {
	padding: 20px 10px;
	
	flex: 1;
	overflow-y: auto;
}

.chat-sidebar-users-list {
	flex: 1;
	width: 100%;
	margin: 0;
	display: flex;
	flex-direction: column;
	justify-content: center;
	gap: 5px;

	/* max-height: 300px; */ /* Максимальная высота */
  	overflow-y: auto;
}
.chat-sidebar-users-list a {
	padding: 5px;
	border-radius: 8px;
	transition: background-color .15s ease-in;
}
.chat-sidebar-users-list a:hover {
	background-color: rgba(0, 123, 255, 0.1);
}

.chat-sidebar-users-item {
	
	display: flex;
	align-items: center;
	color: var(--text-light);
	border-radius: 8px;
}

.user-avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	margin-right: 10px;
}

.rating-visualization {
	margin-top: 10px;
}
</style>