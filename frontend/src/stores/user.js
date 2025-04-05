export default {
	state: {
		auth: Boolean(localStorage.getItem('auth')) || false,
		user: JSON.parse(localStorage.getItem('user')) || null,
	},
	getters: {
		isAuth: (state) => state.auth,
		getUser: (state) => state.user,
	},
	mutations: {
		setAuth(state, status) {
			state.auth = status;
			localStorage.setItem('auth', status);
		},
		setUser(state, userData) {
			state.user = userData;
			localStorage.setItem('user', JSON.stringify(userData));
		}
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
	},
};