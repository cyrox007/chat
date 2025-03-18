<template>
    <header class="row app-header" v-show="!isNoAuthenticated">
        <div class="app-menu">
            <ul>
                <li v-for="item in navigation" :key="item.name">
                    <RouterLink v-if="item.path !== '/users/logout'" :to="item.path">
                        <i :class="`fas ${item.icon}`"></i>
                        <span class="menu-text">{{ item.label }}</span>
                    </RouterLink>
                    <a v-else href="#" @click.prevent="handleLogout">
                        <i :class="`fas ${item.icon}`"></i>
                        <span class="menu-text">{{ item.label }}</span>
                    </a>
                </li>
            </ul>
        </div>
    </header>
</template>

<script setup>
import { ref, computed } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import AuthService from '@/API/AuthService';

const route = useRoute();
const router = useRouter();

const isNoAuthenticated = computed(() => route.meta.requestGuest);

const navigation = ref([
    {
        path: '/',
        name: 'chats',
        label: 'Чаты',
        icon: 'fa-comments',
    },
    {
        path: '/profile',
        name: 'profile',
        label: 'Профиль',
        icon: 'fa-user-circle',
    },
    {
        path: '/messages',
        label: 'Сообщения',
        icon: 'fa-envelope',
    },
    {
        path: '/settings',
        label: 'Настройки',
        icon: 'fa-cog',
    },
    {
        path: '/admin',
        label: 'Админка',
        icon: 'fa-user-shield',
    },
    {
        path: '/users/logout',
        label: 'Выход',
        icon: 'fa-sign-out-alt',
    },
]);

const handleLogout = async () => {
    try {
        // Отправляем запрос на сервер для выхода
        const response = await AuthService.logout();

        // Проверяем статус ответа
        if (response.status === 'ok') {
            // Очищаем localStorage
            localStorage.clear();

            // Перенаправляем на страницу входа
            router.push('/login');
        } else {
            console.error('Unexpected server response:', response);
        }
    } catch (error) {
        console.error('Logout failed:', error);
    }
};
</script>

<style>
.chat-container .app-menu {
	width: 100%;
	display: flex;
	justify-content: center;
	background-color: #f8f9fa;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.chat-container .app-menu ul {
	width: 100%;
	list-style: none;
	display: flex;
	justify-content: space-around;
}

.chat-container .app-menu ul li {
	flex: 1 1 100%;
	padding: 10px 0;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: background-color 0.3s;
}

.chat-container .app-menu ul li:hover {
	background-color: #e9ecef;
	border-radius: 5px;
}

.chat-container .app-menu ul li i {
	margin-right: 8px;
	font-size: 20px;
}

.chat-container .app-menu ul li a {
	text-decoration: none;
	color: inherit;
}

.chat-container .app-menu ul li .menu-text {
	display: inline;
	font-weight: 500;
	color: #343a40;
}

@media (max-width: 768px) {
	.chat-container .app-menu ul li .menu-text {
		display: none;
	}
}
</style>