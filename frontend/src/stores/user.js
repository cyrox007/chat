import { createStore } from 'vuex';
import AuthService from '@/API/AuthService';

export default createStore({
	state: {
		auth: Boolean(localStorage.getItem('auth')) || false,
		user: null, // Храним данные пользователя
	},
	getters: {
		isAuth(state) {
			return state.auth;
		},
		getUser(state) {
			return state.user;
		},
	},
	mutations: {
		setAuth(state, status) {
			state.auth = status;
		},
		setUser(state, userData) {
			state.user = userData;
		},
		clearUser(state) {
			state.user = null;
			state.auth = false;
		},
	},
	actions: {
		
	},
});
