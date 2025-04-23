import { createRouter, createWebHistory } from 'vue-router';
import { useStore } from 'vuex';

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes: [
		{
			path: '/login',
			name: 'login',
			component: () => import('../views/LoginView.vue'),
			meta: {
				title: "Авторизация",
				requestGuest: true // Разрешить доступ только неавторизованным пользователям
			}
		},
		{
			path: '/registration',
			name: 'registration',
			component: () => import('../views/RegistrationView.vue'),
			meta: {
				title: "Регистрация",
				requestGuest: true // Разрешить доступ только неавторизованным пользователям
			}
		},
		{
			path: '/',
			name: 'chats',
			component: () => import('../views/MainView.vue'),
			meta: {
				title: "Чаты",
				requestAuth: true
			}
		},
		{
			path: '/profile',
			name: 'Profile',
			component: () => import('../views/ProfileView.vue'),
			meta: {
				title: "Профиль",
				requestAuth: true
			}
		},
		{
			path: '/profile/:uid',
			name: 'UserProfile',
			component: () => import('../views/ProfileView.vue'),
			meta: {
				title: "Профиль",
				requestAuth: true
			}
		},
		{
			path: '/messenger',
			name: 'messenger',
			component: () => import('../views/MessengerView.vue'),
			meta: {
				title: "Сообщения",
				requestAuth: true
			}
		},
		{
			path: '/admin',
			name: 'AdminDashboard',
			component: () => import('../views/AdminLayout.vue'),
			meta: {
				requestAuth: true,
				requiresAdmin: true
			},
			children: [
				{
					path: '',
					name: 'AdminDashboardHome',
					component: () => import('../views/AdminPanel/DashboardView.vue'),
					meta: { title: 'Админ панель - Консоль' }
				},
				{
					path: '/admin/profile/:uid',
					name: 'AdminProfileView',
					component: () => import('../views/AdminPanel/AdminProfileView.vue'),
					meta: {
						title: "Админ панель - Профиль",
						requestAuth: true,
						requiresAdmin: true
					}
				},
				{
					path: '/admin/profiles',
					name: 'AdminProfileList',
					component: () => import('../views/AdminPanel/AdminProfileList.vue'),
					meta: {
						title: "Админ панель - Список пользователей",
						requestAuth: true,
						requiresAdmin: true
					}
				},
			]
		},

		// Маршрут для 404 ошибки (не найдено)
		{
			path: '/:pathMatch(.*)*',
			name: 'NotFound',
			component: () => import('../views/NotFoundView.vue'),
			meta: {
				title: "Страница не найдена"
			}
		}
		/*{
			path: '/settings',
			name: 'settings',
			component: () => import('../views/SettingsView.vue'),
			meta: {
				title: "Настройки",
				requestAuth: true
			}
		} */
	]
});

// Навигация и проверка аутентификации остаются прежними
router.beforeEach(async (to, from, next) => {
	document.title = to.meta.title || 'По умолчанию';

	const store = useStore();
	const isAuthenticated = localStorage.getItem('access_token');
	const userRole = store.getters['getUser']?.global_role;

	// Проверка для гостевых маршрутов
	if (to.matched.some(record => record.meta.requestGuest)) {
		if (isAuthenticated) {
			return next({ name: 'chats' });
		}
		return next();
	}

	// Проверка для защищенных маршрутов
	if (to.matched.some(record => record.meta.requestAuth)) {
		if (!isAuthenticated) {
			return next({ name: 'login' });
		}

		// Дополнительная проверка для админских маршрутов
		if (to.matched.some(record => record.meta.requiresAdmin)) {
			if (userRole !== 'admin' && userRole !== 'superadmin') {
				// Можно перенаправить на главную или показать страницу "Доступ запрещен"
				return next({ name: 'chats' });
			}
		}

		return next();
	}

	next();
});

export default router;