import { defineStore } from 'pinia';

export const useChatStore = defineStore('chat', {
	state: () => ({
		currentRoom: null, // Текущая комната
		connectedUsers: [], // Подключенные пользователи
		currentUser: null, // Текущий пользователь
	}),
	actions: {
		setCurrentRoom(room) {
			this.currentRoom = room;
		},
		clearCurrentRoom() {
			this.currentRoom = null;
		},
		setConnectedUsers(users) {
			this.connectedUsers = users;
		},
		setCurrentUser(user) {
			this.currentUser = user;
		},
		clearCurrentUser() {
			this.currentUser = null;
		},
	},
});