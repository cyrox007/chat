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
            <p><strong>Страна:</strong> {{ roomInfo.country }}</p>
            <p><strong>Регион:</strong> {{ roomInfo.region }}</p>
            <p><strong>Теги:</strong> {{ roomInfo.tags }}</p>
            <p><strong>Дата создания:</strong> {{ formatDate(roomInfo.created_at) }}</p>
            <p><strong>Владелец:</strong> 
                <router-link v-if="owner" :to="`/profile/${owner.uid}`">{{ owner.username }}</router-link>
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
            <h3>Пользователи</h3>
            <ul v-if="users.length > 0">
                <li v-for="user in users" :key="user.uid" class="user" :data-user-id="user.uid">
                    <img :src="user.avatar" alt="Avatar" class="user-avatar">
                    <router-link :to="`/profile/${user.uid}`" class="username">{{ user.username }}</router-link>
                </li>
            </ul>
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
/* .chat-sidebar-right {
    position: fixed;
    top: 0;
    right: 0;
    width: 300px;
    height: 100vh;
    background-color: #fff;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    transform: translateX(100%);
    transition: transform 0.3s ease-in-out;
}

.chat-sidebar-right.active {
    transform: translateX(0);
}  */

.close-sidebar {
    position: absolute;
    top: 10px;
    right: 10px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 20px;
    color: #888;
}

.chat-sidebar-info {
    padding: 20px;
    border-bottom: 1px solid #ddd;
}

.chat-sidebar-users {
    padding: 20px;
}

.user {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
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