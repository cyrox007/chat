import NotificationService from '@/API/NotificationService';

const POLL_INTERVAL_MS = 180000;
let pollingTimer = null;

const normalizeUnread = (value) => Math.max(0, Number(value) || 0);

export default {
	namespaced: true,
	state: {
		unread: 0,
		syncing: false,
		initialized: false,
	},
	getters: {
		unread: (state) => state.unread,
		syncing: (state) => state.syncing,
		initialized: (state) => state.initialized,
	},
	mutations: {
		setUnread(state, value) {
			state.unread = normalizeUnread(value);
		},
		setSyncing(state, value) {
			state.syncing = Boolean(value);
		},
		setInitialized(state, value) {
			state.initialized = Boolean(value);
		},
	},
	actions: {
		async refreshUnread({ commit }) {
			const response = await NotificationService.unreadCount();
			commit('setUnread', response.data.unread);
			commit('setInitialized', true);
			return response.data.unread;
		},
		async sync({ commit, state }) {
			if (state.syncing) return state.unread;
			commit('setSyncing', true);
			try {
				const response = await NotificationService.sync();
				commit('setUnread', response.data.unread);
				commit('setInitialized', true);
				return response.data.unread;
			} finally {
				commit('setSyncing', false);
			}
		},
		setUnread({ commit }, value) {
			commit('setUnread', value);
		},
		decrementUnread({ commit, state }, amount = 1) {
			commit('setUnread', Math.max(0, state.unread - Math.max(0, Number(amount) || 0)));
		},
		clear({ commit }) {
			commit('setUnread', 0);
			commit('setInitialized', false);
			commit('setSyncing', false);
		},
		startPolling({ dispatch }) {
			if (pollingTimer) return;
			pollingTimer = window.setInterval(() => {
				dispatch('sync').catch(() => {
					// Polling is best-effort and must never break the app shell.
				});
			}, POLL_INTERVAL_MS);
		},
		stopPolling() {
			if (!pollingTimer) return;
			window.clearInterval(pollingTimer);
			pollingTimer = null;
		},
	},
};

export { POLL_INTERVAL_MS };
