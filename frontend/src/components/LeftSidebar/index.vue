<template>
	<aside class="chat-sidebar-left">
		<button class="close-sidebar" aria-label="Закрыть сайдбар" @click="closeSidebar">
			<i class="fas fa-arrow-left"></i>
		</button>
		<div class="search-container">
			<input type="text" placeholder="Поиск чатов..." />
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
import { defineProps, defineEmits } from 'vue';

const props = defineProps({
	isActive: {
		type: Boolean,
		default: false,
	},
	rooms: {
		type: Array,
		required: true
	}
});
const emit = defineEmits(['close', 'switch-room']);
// Функция для закрытия сайдбара
const closeSidebar = () => {
	emit('close');
};
const selectRoom = (room) => {
	// Эмитируем событие для переключения комнаты
	emit('switch-room', room);
};
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

.chat-sidebar-left .search-container {
	padding-bottom: 10px;
	border-bottom: 1px solid #ccc;
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
</style>