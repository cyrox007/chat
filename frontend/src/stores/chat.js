export default {
	namespaced: true, // Включаем пространства имен
	state: {
		currentRoom: null, // Текущая комната
		connectedUsers: [], // Подключенные пользователи
	},
	getters: {
		getCurrentRoom: (state) => state.currentRoom,
		getConnectedUsers: (state) => state.connectedUsers,
	},
	mutations: {
		setCurrentRoom(state, room) {
			state.currentRoom = room;
		},
		clearCurrentRoom(state) {
			state.currentRoom = null;
		},
		setConnectedUsers(state, users) {
			state.connectedUsers = users;
		},
	},
	actions: {
		updateCurrentRoom({ commit }, room) {
			commit('setCurrentRoom', room);
		},
		clearChatState({ commit }) {
			commit('clearCurrentRoom');
			commit('setConnectedUsers', []);
		},
		updateConnectedUsers({ commit }, users) {
			commit('setConnectedUsers', users);
		},
	},
};