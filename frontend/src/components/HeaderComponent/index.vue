<template>
	<header class="app-header">
		<!-- Логотип сайта -->
		<div class="site-logo">
			<a href="/">
				<!-- <img src="@/assets/logo.png" alt="Логотип сайта" /> -->
				<span>ЧАТ</span>
			</a>
		</div>

		<!-- Пользовательское меню (правая часть) -->
		<nav style="display: flex;">
			<!-- Навигационное меню -->
			<div class="app-menu" v-if="!isAuthenticated">
				<ul>
					<li>
						<router-link to="/login">Авторизация</router-link>
					</li>
					<li>
						<router-link to="/registration">Регистрация</router-link>
					</li>
				</ul>
			</div>
			
			<div class="user-profile user-menu" v-if="currentUser.uid">
				<div class="user-avatar" @click="toggleDropdown">
					<img :src="currentUser.avatar" alt="Аватар пользователя" />
				</div>
				<ul v-show="isDropdownOpen">
					<li v-for="(item, index) in navigation" :key="index">
						<router-link v-if="item.path !== '/users/logout'"
							:to="item.params ? { path: item.path, params: item.params } : { path: item.path }"
							@click.native="handleMenuClick(item)">
							<i :class="`fas ${item.icon}`"></i>
							<span class="menu-text">{{ item.label }}</span>
						</router-link>
						<a v-else href="#" @click.prevent="handleLogout">
							<i :class="`fas ${item.icon}`"></i>
							<span class="menu-text">{{ item.label }}</span>
						</a>
					</li>
				</ul>
			</div>
			<!-- Темная тема -->
			<button class="theme-toggle-btn" @click="toggleTheme">
				<i :class="currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon'"></i>
			</button>
		</nav>
		
	</header>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import AuthService from '@/API/AuthService';
import { useStore } from 'vuex';

/* const route = useRoute(); */
const router = useRouter();
const store = useStore();

// Состояние текущей темы
const currentTheme = ref('light');

// Флаг для выпадающего меню
const isDropdownOpen = ref(false);

// Переключение выпадающего меню
const toggleDropdown = () => {
	isDropdownOpen.value = !isDropdownOpen.value;
};

// Проверка на неавторизованный режим
const isAuthenticated = computed(() => { return store.getters.isAuth });

// Получение текущего пользователя
const currentUser = computed(() => {
	return store.getters.getUser || { uid: null };
});

// Проверка роли администратора
const isAdmin = computed(() => {
	const user = store.getters.getUser;
	return user?.global_role === 'admin' || user?.global_role === 'superadministrator';
});

// Генерация навигации
const navigation = computed(() => {
	const baseNavigation = [
		{
			path: `/profile/${currentUser.value.uid}`,
			name: 'profile',
			label: currentUser.value.first_name && currentUser.value.last_name ? `${currentUser.value.first_name} ${currentUser.value.last_name}` : `${currentUser.value.username}`,
			icon: 'fa-user-circle',
		},
		{
			path: '/',
			name: 'chats',
			label: 'Чаты',
			icon: 'fa-comments',
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
			path: '/users/logout',
			label: 'Выход',
			icon: 'fa-sign-out-alt',
		},
	];

	if (isAdmin.value) {
		baseNavigation.splice(4, 0, {
			path: '/admin',
			label: 'Админка',
			icon: 'fa-user-shield',
		});
	}

	return baseNavigation;
});

// Обработка клика по меню
const handleMenuClick = (item) => {
	if (item.path === '/profile') {
		console.log('Перезагрузка данных профиля...');
	}
};

// Обработка выхода
const handleLogout = async () => {
	try {
		const response = await AuthService.logout();

		if (response.data.status === 'ok') {
			store.dispatch('clearUser');
			/* localStorage.clear(); */
			window.location.href = '/login'
		} else {
			console.error('Unexpected server response:', response);
		}
	} catch (error) {
		console.error('Logout failed:', error);
	}
};

// Загрузка сохраненной темы из localStorage
onMounted(() => {
	const savedTheme = localStorage.getItem('theme') || 'light';
	currentTheme.value = savedTheme;
	applyTheme(savedTheme);
});

// Переключение темы
const toggleTheme = () => {
	const newTheme = currentTheme.value === 'light' ? 'dark' : 'light';
	currentTheme.value = newTheme;
	applyTheme(newTheme);
	localStorage.setItem('theme', newTheme); // Сохраняем выбранную тему
};

// Применение темы
const applyTheme = (theme) => {
	const root = document.documentElement;
	if (theme === 'dark') {
		root.style.setProperty('--bg-light', '#212529');
		root.style.setProperty('--text-light', '#ffffff');
		root.style.setProperty('--profile-bg-light', '#343a40');
		root.style.setProperty('--profile-details-color', '#adb5bd');
	} else {
		root.style.setProperty('--bg-light', '#f8f9fa');
		root.style.setProperty('--text-light', '#212529');
		root.style.setProperty('--profile-bg-light', '#f0f4fc');
		root.style.setProperty('--profile-details-color', '#6c757d');
	}
};
</script>

<style scoped>
/* Общие стили */
.app-header {
	position: relative;
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 10px 20px;
	background-color: var(--bg-light);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	max-height: 50px;
}

.site-logo {
	margin-right: auto;
	font-size: 1.5rem;
	font-weight: bold;
	color: var(--text-light);
	cursor: pointer;
}

.site-logo span {
	text-decoration: none;
	color: inherit;
}

/* Навигационное меню */
.app-menu ul {
	list-style: none;
	display: flex;
	gap: 20px;
}

.app-menu li {
	display: flex;
	align-items: center;
	cursor: pointer;
	transition: color 0.3s ease;
}

.app-menu li:hover {
	color: var(--primary-color);
}

.app-menu a {
	text-decoration: none;
	color: inherit;
}

/* Пользовательское меню */
.user-profile {
	position: relative;
}
.user-avatar {
	display: flex;
	align-items: center;
	justify-content: center;
}
.user-avatar img {
	width: 30px;
	height: 30px;
	border-radius: 50%;
	object-fit: cover;
	cursor: pointer;
}

.user-menu ul {
	position: absolute;
	top: calc(100% + 10px);
	right: 0;
	background: #fff;
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	border-radius: 4px;
	padding: 10px;
	z-index: 1000;
	flex-direction: column;
	min-width: 150px;
}

.user-menu ul li {
	display: flex;
	align-items: center;
	gap: 5px;
	padding: 8px 12px;
	border-radius: 4px;
	transition: background 0.3s ease;

}

.user-menu ul li:hover {
	background: #f1f1f1;
}

.user-menu ul li a {
	text-decoration: none;
	color: inherit;
	width: 100%;
	display: flex;
	align-items: center;
	gap: 5px;
}

/* Темная тема кнопка */
.theme-toggle-btn {
	background: none;
	border: none;
	font-size: 20px;
	cursor: pointer;
	color: var(--text-light);
	margin-left: 10px;
}

/* Адаптация для мобильных устройств */
@media (max-width: 768px) {
	.app-header {
		/* flex-direction: column; */
		/* align-items: flex-start; */
		gap: 10px;
	}

	.site-logo {
		margin-right: 0;
	}

	.app-menu ul {
		/* flex-direction: column; */
		gap: 10px;
	}

	.user-menu ul {
		right: unset;
		right: 0;
		width: 100%;
	}
}
</style>