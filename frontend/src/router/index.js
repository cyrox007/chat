import { createRouter, createWebHistory } from 'vue-router';

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
		/*{
			path: '/settings',
			name: 'settings',
			component: () => import('../views/SettingsView.vue'),
			meta: {
				title: "Настройки",
				requestAuth: true
			}
		},
		{
			path: '/admin',
			name: 'admin',
			component: () => import('../views/AdminView.vue'),
			meta: {
				title: "Админка",
				requestAuth: true
			}
		},
		{
			path: '/logout',
			name: 'logout',
			component: () => import('../views/LogoutView.vue'),
			meta: {
				title: "Выход",
				requestAuth: true
			}
		} */
	]
});

// Навигация и проверка аутентификации остаются прежними
router.beforeEach((to, from, next) => {
	document.title = to.meta.title || 'По умолчанию';

	if (to.matched.some(record => record.meta.requestAuth)) {
		if (localStorage.getItem('access_token')) {
			next();
		} else {
			next({ name: 'login' });
		}
	} else if (to.matched.some(record => record.meta.requestGuest)) {
		if (localStorage.getItem('access_token')) {
			next({ name: 'chats' });
		} else {
			next();
		}
	} else {
		next();
	}
});

export default router;