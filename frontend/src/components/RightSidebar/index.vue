<template>
    <aside class="chat-sidebar-right" :class="{ active: isActive }">
        <!-- Кнопка закрытия -->
        <button class="close-sidebar" aria-label="Закрыть сайдбар" @click="closeSidebar">
            <i class="fas fa-times"></i>
        </button>

        <!-- Информация о комнате -->
        <div class="chat-sidebar-info">
            <h3>Информация о комнате</h3>
            <p><strong>Название:</strong> {{ roomInfo.name }}</p>
            <p><strong>Описание:</strong> {{ roomInfo.description || 'Нет описания' }}</p>
        </div>

        <!-- Список пользователей -->
        <div class="chat-sidebar-users">
            <h3>Пользователи</h3>
            <ul v-if="users.length > 0">
                <li v-for="user in users" :key="user.uid" class="user" :data-user-id="user.uid">
                    <img :src="user.avatar" alt="Avatar" class="user-avatar">
                    <span class="username">{{ user.username }}</span>
                </li>
            </ul>
            <p v-else>Нет подключенных пользователей</p>
        </div>
    </aside>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

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

// Функция для закрытия сайдбара
const closeSidebar = () => {
    emit('close');
};
</script>