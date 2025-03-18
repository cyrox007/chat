<template>
    <aside class="chat-sidebar-left">
        <button class="close-sidebar" aria-label="Закрыть сайдбар" @click="closeSidebar">
            <i class="fas fa-times"></i>
        </button>
        <div class="search-container">
            <input type="text" placeholder="Поиск чатов..." />
        </div>
        <div class="chat-list">
            <h4>Чаты</h4>
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