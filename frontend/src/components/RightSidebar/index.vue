<template>
    <aside class="chat-sidebar-right" :class="{ active: isActive }">
        <button class="close-sidebar" aria-label="Закрыть сайдбар" @click="closeSidebar">
            <i class="fas fa-times"></i>
        </button>
        <div class="chat-sidebar-info">
            <h3>Информация о чате</h3>
            <p>Здесь будет информация о чате.</p>
        </div>

        <div class="chat-sidebar-users">
            <h3>Пользователи</h3>
            <ul>
                <li class="user" data-user-id="1">
                    <img src="https://lastfm.freetls.fastly.net/i/u/ar0/21ca516943664822c82bd00ca9a9ea7c.png" alt="Avatar" class="user-avatar">
                    <span class="username">Пользователь 1</span>
                </li>
                <li class="user" data-user-id="2">
                    <img src="https://cdn1.flamp.ru/4adc8b88cb413fcb010f66eab1ed86a5.jpg" alt="Avatar" class="user-avatar">
                    <span class="username">Пользователь 2</span>
                </li>
                <li class="user" data-user-id="3">
                    <img src="https://i1.sndcdn.com/avatars-000548549298-oy0h9i-t1080x1080.jpg" alt="Avatar" class="user-avatar">
                    <span class="username">Пользователь 3</span>
                </li>
            </ul>
        </div>
        
    </aside>
</template>

<script setup>
import { defineProps } from 'vue';

const props = defineProps({
    isActive: {
        type: Boolean,
        default: false,
    },
});
const emit = defineEmits(['close']);
// Функция для закрытия сайдбара
const closeSidebar = () => {
    emit('close');
};
</script>