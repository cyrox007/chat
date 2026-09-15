import CSRFService from "@/API/CSRFService";
import UsersServices from "@/API/UsersService";
import AuthService from "@/API/AuthService";

const readJSON = (key) => {
	try {
		const value = localStorage.getItem(key);
		return value ? JSON.parse(value) : null;
	} catch {
		return null;
	}
};

export default {
	state: {
		auth: Boolean(localStorage.getItem('access_token')),
		user: readJSON('user'),
		identity: readJSON('identity'),
		userStatuses: {},
	},
	getters: {
		isAuth: (state) => state.auth,
		getUser: (state) => state.user,
		getIdentity: (state) => state.identity,
		getPersona: (state) => state.identity?.persona || null,
		getAccount: (state) => state.identity?.account || null,
		getUserStatus: (state) => (userId) => state.userStatuses[userId],
	},
	mutations: {
		setAuth(state, status) {
			state.auth = status;
			if (status) {
				localStorage.setItem('auth', 'true');
			} else {
				localStorage.removeItem('auth');
			}
		},
		setUser(state, userData) {
			state.user = userData ? { ...userData } : null;
			if (userData) {
				localStorage.setItem('user', JSON.stringify(userData));
			} else {
				localStorage.removeItem('user');
			}
		},
		setIdentity(state, identity) {
			state.identity = identity ? { ...identity } : null;
			if (identity) {
				localStorage.setItem('identity', JSON.stringify(identity));
			} else {
				localStorage.removeItem('identity');
			}
		},
		setMultipleUserStatuses(state, statuses) {
			state.userStatuses = { ...state.userStatuses, ...statuses };
		},
		clearUserStatus(state, userId) {
			delete state.userStatuses[userId];
		},
	},
	actions: {
		clearUser({ commit }) {
			commit('setUser', null);
			commit('setIdentity', null);
			commit('setAuth', false);
			localStorage.removeItem('access_token');
		},
		async applyIdentitySession({ commit }, responseData) {
			localStorage.setItem('access_token', responseData.access_token);
			commit('setUser', responseData.user);
			commit('setIdentity', {
				account: responseData.account,
				persona: responseData.persona,
				privacy: responseData.privacy,
				role: responseData.role,
			});
			commit('setAuth', true);
		},
		async logout({ dispatch }) {
			try {
				await AuthService.logout();
			} finally {
				await dispatch('messenger/disconnectMessenger', null, { root: true });
				await dispatch('chat/disconnectSocket', null, { root: true });
				await dispatch('clearUser');
			}
			return true;
		},
		initializeUser({ commit }) {
			const accessToken = localStorage.getItem('access_token');
			const user = readJSON('user');
			const identity = readJSON('identity');

			if (accessToken && user) {
				commit('setAuth', true);
				commit('setUser', user);
				if (identity) commit('setIdentity', identity);
				return;
			}

			commit('setAuth', false);
			commit('setUser', null);
			commit('setIdentity', null);
		},
		async syncIdentity({ commit, dispatch }) {
			try {
				const response = await AuthService.me();
				commit('setUser', response.data.user);
				commit('setIdentity', {
					account: response.data.account,
					persona: response.data.persona,
					privacy: response.data.privacy,
					role: response.data.role,
				});
				return response.data;
			} catch (error) {
				if (error.response?.status === 401) await dispatch('clearUser');
				throw error;
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
