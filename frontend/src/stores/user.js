import CSRFService from "@/API/CSRFService";
import UsersServices from "@/API/UsersService";
export default {
	state: {
		auth: Boolean(localStorage.getItem('auth')) || false,
		user: JSON.parse(localStorage.getItem('user')) || null,
		userStatuses: {},
	},
	getters: {
		isAuth: (state) => state.auth,
		getUser: (state) => state.user,
		getUserStatus: (state) => (userId) => state.userStatuses[userId],
	},
	mutations: {
		setAuth(state, status) {
			state.auth = status;
			localStorage.setItem('auth', status);
		},
		setUser(state, userData) {
			state.user = userData;
			localStorage.setItem('user', JSON.stringify(userData));
		},
		setMultipleUserStatuses(state, statuses) {
			state.userStatuses = { ...state.userStatuses, ...statuses };
		},
		clearUserStatus(state, userId) {
			delete state.userStatuses[userId];
		},
	},
	actions: {
		clearUser(state) {
			state.user = null;
			state.auth = false;
			localStorage.removeItem('auth');
			localStorage.removeItem('user');
			localStorage.clear();
		},
		initializeUser({ commit }) {
			const auth = Boolean(localStorage.getItem('auth'));
			const user = JSON.parse(localStorage.getItem('user'));

			if (auth && user) {
				commit('setAuth', true);
				commit('setUser', user);
			} else {
				dispatchEvent('clearUser');
			}
		},
		async fetchUserStatuses({ commit }, userIds) {
			try {
				await CSRFService.getCSRF();			
				const response = await UsersServices.getUserStatuses(userIds);
				if (response.data.status === 'ok') {
					commit('setMultipleUserStatuses', response.data.statuses);
				}
			} catch (error) {
				console.error('Ошибка при получении статусов пользователей:', error);
			}
		},
	},
};