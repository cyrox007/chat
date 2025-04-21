<template>
	<aside class="chat-sidebar-left">
		<button class="close-sidebar" aria-label="Закрыть сайдбар" @click="closeSidebar">
			<i class="fas fa-arrow-left"></i>
		</button>
		<div class="sidebar-header">
			<div class="search-container">
				<input type="text" placeholder="Поиск чатов..." disabled />
			</div>
			<div class="create-chat">
                <!-- Кнопка создания чата -->
                <button v-if="canCreateChat" @click="emitCreateChatModal">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
		</div>
		<div class="chat-list">
			<!-- <h4>Чаты</h4> -->
			<ul>
				<li v-for="room in rooms" :key="room.id" @click="selectRoom(room)">
					{{ room.name }}
				</li>
			</ul>
		</div>
	</aside>
</template>

<script setup>
import { defineProps, defineEmits, computed } from 'vue';

const props = defineProps({
	isActive: {
		type: Boolean,
		default: false,
	},
	rooms: {
		type: Array,
		required: true
	},
	userRole: {
		type: String,
		default: 'user' // Роль пользователя (например, 'user', 'moderator', 'admin')
	},
	userRating: {
		type: Number,
		default: 0 // Рейтинг пользователя
	}
});

const emit = defineEmits(['close', 'switch-room', 'open-create-chat-modal']);

// Функция для закрытия сайдбара
const closeSidebar = () => {
	emit('close');
};

const selectRoom = (room) => {
	// Эмитируем событие для переключения комнаты
	emit('switch-room', room);
};

// Функция для эмитирования события открытия модального окна создания чата
const emitCreateChatModal = () => {
	emit('open-create-chat-modal');
};

// Вычисляемое свойство для проверки прав на создание чата
const canCreateChat = computed(() => {
	const isModeratorOrHigher = ['moderator', 'admin', 'superadmin'].includes(props.userRole);
	const hasSufficientRating = props.userRating >= 500; // Например, минимальный рейтинг 50
	return isModeratorOrHigher || hasSufficientRating;
});
</script>

<style>
.chat-sidebar-left {
	position: relative;
	height: 100%;
	min-width: 300px;
	width: 300px;
	/* width: 25%; */
	padding: 10px;
	background-color: var(--sidebar-bg-light);
	transition: transform 0.3s ease-in-out, opacity 0.3s ease-in-out;
}

@media screen and (max-width: 720px) {
	.chat-sidebar-left {
		position: absolute;
		left: 0;
		transform: translateX(-120%);
		z-index: 9999;
	}
	.chat-sidebar-left.active {
		transform: translateX(0%);
	}
}

@media screen and (max-width: 720px) {
	.chat-sidebar-left {
		height: calc(100% - (50px + 8px));
	}
}

.close-sidebar {
	cursor: pointer;
	position: absolute;
	top: 15px;
	right: -18px;
	background: none;
	border: none;
	display: none;
	background-color: #ccc;
	border-radius: 100%;
	padding: 5px;
	width: 30px;
	height: 30px;
}

@media screen and (max-width: 720px) {
	.close-sidebar {
		display: block;
	}
}

.chat-sidebar-left .sidebar-header {
	display: flex;
	gap: 5px;
	border-bottom: 1px solid #ccc;
}

.chat-sidebar-left .sidebar-header .search-container {
	flex: 1;
	padding-bottom: 10px;
}

.chat-sidebar-left .search-container input {
	width: 100%;
	padding: 10px;
	border: 1px solid #ccc;
	border-radius: 5px;
	transition: border-color 0.3s;
}

.chat-sidebar-left .search-container input:focus {
	border-color: var(--primary-color);
	outline: none;
}

.chat-sidebar-left .chat-list {
	margin-top: 10px;
	margin-bottom: 15px;
}

.chat-sidebar-left .chat-list h4 {
	font-size: 1.2em;
	margin-bottom: 5px;
	color: var(--text-light);
}

.chat-sidebar-left .chat-list ul {
	list-style-type: none;
	padding: 0;
	margin: 0;
}

.chat-sidebar-left .chat-list ul li {
	cursor: pointer;
	padding: 10px;
	border-radius: 5px;
	transition: background-color 0.3s;
}

.chat-sidebar-left .chat-list ul li:hover {
	background-color: rgba(0, 123, 255, 0.1);
}
.create-chat {
	padding-bottom: 10px;
}
.create-chat button {
	width: 38px;
	height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 5px;
    padding: 8px 8px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s ease;
}

.create-chat button:hover {
    background-color: var(--primary-color-hover);
}
</style>