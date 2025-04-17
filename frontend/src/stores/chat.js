import UsersService from '@/API/UsersService';
import CSRFService from '@/API/CSRFService';

export default {
	namespaced: true,
	state: {
		currentRoom: null,
		connectedUsers: [],
		socket: null,
		isConnected: false,
		messages: [],
		notifications: [],
		unreadReplies: []
	},
	getters: {
		getCurrentRoom: (state) => state.currentRoom,
		getConnectedUsers: (state) => state.connectedUsers,
		isConnected: (state) => state.isConnected,
		getMessages: (state) => state.messages,
		unreadReplies: (state) => state.unreadReplies,
  		hasUnreadReplies: (state) => state.unreadReplies.length > 0
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
		setSocket(state, socket) {
			state.socket = socket;
		},
		setConnectionStatus(state, status) {
			state.isConnected = status;
		},
		addMessage(state, message) {
			state.messages.push(message);
		},
		clearMessages(state) {
			state.messages = [];
		},
		ADD_UNREAD_REPLY(state, reply) {
			state.unreadReplies.push(reply);
		  },
		  CLEAR_UNREAD_REPLIES(state) {
			state.unreadReplies = [];
		  }
	},
	actions: {
		async fetchUserData({ commit }, userUids) {
			try {
				await CSRFService.getCSRF();
				const response = await UsersService.get_users_by_uids(userUids);
				if (response.data.status === 'ok') {
					return response.data.users;
				}
				return [];
			} catch (error) {
				console.error('Ошибка загрузки данных пользователей:', error);
				return [];
			}
		},

		async connectSocket({ commit, state, dispatch }, roomId) {
			try {
				// Закрываем предыдущее соединение
				if (state.socket) {
					state.socket.close();
					commit('setSocket', null);
					commit('setConnectionStatus', false);
				}

				const token = localStorage.getItem('access_token');
				if (!token) {
					throw new Error('Токен не найден');
				}

				const wsServerUrl = import.meta.env.VITE_API_WS_SERVER_URL || 'ws://localhost:9000';
				const socket = new WebSocket(`${wsServerUrl}/ws/${token}/rooms/${roomId}`);

				commit('setSocket', socket);

				socket.onopen = () => {
					console.log('WebSocket соединение установлено');
					commit('setConnectionStatus', true);
				};

				socket.onclose = (event) => {
					console.log('WebSocket соединение закрыто', event);
					commit('setConnectionStatus', false);
					// Убрали автоматический реконнект
				};

				socket.onerror = (error) => {
					console.error('WebSocket ошибка:', error);
					commit('setConnectionStatus', false);
				};

				socket.onmessage = (event) => {
					try {
						const data = JSON.parse(event.data);
						dispatch('handleSocketMessage', data);
					} catch (error) {
						console.error('Ошибка обработки сообщения:', error);
					}
				};

			} catch (error) {
				console.error('Ошибка подключения WebSocket:', error);
				commit('setConnectionStatus', false);
				throw error;
			}
		},

		async handleSocketMessage({ commit, dispatch, rootGetters }, data) {
			const currentRoute = window.location.pathname;
			const currentUser = rootGetters['getUser']; // Исправляем на полный путь
			const currentUserId = currentUser?.uid;

			switch (data.type) {
				case 'message':
					commit('addMessage', data);
					
					if (currentRoute !== '/') {

						if (data.reply_to?.sender?.uid === currentUserId) {
							const reply = {
							  uid: data.uid,
							  sender: data.sender,
							  content: data.content,
							  room_uid: data.room_uid,
							  timestamp: new Date(data.created_at || new Date())
							};
							
							commit('ADD_UNREAD_REPLY', reply);
							dispatch('playNotificationSound');
						  }
					}
					break;

				case 'user_list':
					try {
						const usersData = await dispatch('fetchUserData', data.users);
						commit('setConnectedUsers', usersData);
					} catch (error) {
						console.error('Ошибка загрузки пользователей:', error);
					}
					break;

				case 'initial_data':
					if (Array.isArray(data.messages)) {
						commit('clearMessages');
						data.messages.reverse().forEach(msg => commit('addMessage', msg));
					}
					break;

				case 'ping':
					if (state.socket) {
						state.socket.send(JSON.stringify({ type: 'pong' }));
					}
					break;

				default:
					console.warn('Неизвестный тип сообщения:', data.type);
			}
		},

		disconnectSocket({ commit, state }) {
			if (state.socket) {
				state.socket.close();
				commit('setSocket', null);
				commit('setConnectionStatus', false);
				commit('clearMessages');
				commit('CLEAR_UNREAD_REPLIES');
			}
		},

		sendMessage({ state }, message) {
			if (state.socket && state.socket.readyState === WebSocket.OPEN) {
				state.socket.send(JSON.stringify(message));
			} else {
				throw new Error('WebSocket не подключен');
			}
		},

		clearNotifications({ commit }) {
			commit('CLEAR_UNREAD_REPLIES');
		},

		async switchRoom({ dispatch, commit }, { room, roomId }) {
			// Очищаем предыдущие данные
			commit('clearMessages');
			commit('CLEAR_UNREAD_REPLIES');

			// Устанавливаем новую комнату и подключаемся
			commit('setCurrentRoom', room);
			await dispatch('connectSocket', roomId);
		},

		playNotificationSound() {
			// Используем путь из public, а не из assets
			const audio = new Audio('/sounds/chat_notification.mp3');
		
			// Предварительная загрузка и обработка ошибок
			audio.preload = 'auto';
		
			// Обработка событий загрузки
			audio.addEventListener('canplaythrough', () => {
				// Когда аудио готово к воспроизведению
				audio.play().catch((e) => {
					console.error('Ошибка воспроизведения звука:', e);
				});
			});
		
			// Обработка ошибок загрузки
			audio.addEventListener('error', (e) => {
				console.error('Ошибка загрузки аудио:', e);
			});
		
			// Начинаем загрузку
			audio.load();
		}
	}
};