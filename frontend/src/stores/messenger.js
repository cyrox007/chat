export default {
	namespaced: true,
	state: {
		socket: null,
		isConnected: false,
		activeDialog: null,
		conversations: {},
		unreadCounts: {},
		notifications: [],
		onlineStatuses: {}, // { [userId]: boolean }
		statusSubscriptions: new Set()
	},
	getters: {
		getConversation: (state) => (userId) => state.conversations[userId] || [],
		getUnreadCount: (state) => (userId) => state.unreadCounts[userId] || 0,
		getActiveDialog: (state) => state.activeDialog,
		isConnected: (state) => state.isConnected,
		getNotifications: (state) => state.notifications,
		hasUnreadNotifications: (state) => state.notifications.length > 0,
		isUserOnline: (state) => (userId) => state.onlineStatuses[userId] || false,
		getOnlineStatuses: (state) => state.onlineStatuses
	},
	mutations: {
		SET_SOCKET(state, socket) {
			state.socket = socket;
		},
		SET_CONNECTION_STATUS(state, status) {
			state.isConnected = status;
		},
		SET_ACTIVE_DIALOG(state, userId) {
			state.activeDialog = userId;
			if (userId && state.unreadCounts[userId]) {
				state.unreadCounts[userId] = 0;
			}
		},
		ADD_MESSAGE(state, { userId, message }) {
			if (!state.conversations[userId]) {
				state.conversations[userId] = [];
			}
			state.conversations[userId].push(message);

			// Увеличиваем счетчик непрочитанных, если это не активный диалог
			if (state.activeDialog !== userId) {
				state.unreadCounts[userId] = (state.unreadCounts[userId] || 0) + 1;

				// Добавляем уведомление
				state.notifications.push({
					uid: message.uid,
					sender: message.sender,
					content: message.content,
					timestamp: message.timestamp,
					userId: userId,
				});
			}
		},
		CLEAR_NOTIFICATIONS(state) {
			state.notifications = [];
		},
		SET_CONVERSATION(state, { userId, messages }) {
			state.conversations[userId] = messages;
		},
		CLEAR_CONVERSATION(state, userId) {
			delete state.conversations[userId];
		},
		MARK_MESSAGE_AS_READ(state, messageId) {
			for (const userId in state.conversations) {
				const messages = state.conversations[userId];
				const message = messages.find(msg => msg.uid === messageId);
				if (message) {
					message.is_read = true;
				}
			}
		},
		UPDATE_ONLINE_STATUS(state, { userId, isOnline }) {
			state.onlineStatuses[userId] = isOnline;
		},
		UPDATE_STATUS_SUBSCRIPTIONS(state, { userIds, subscribe }) {
			userIds.forEach(userId => {
				if (subscribe) {
					state.statusSubscriptions.add(userId);
				} else {
					state.statusSubscriptions.delete(userId);
				}
			});
		},
		CLEAR_STATUS_SUBSCRIPTIONS(state) {
			state.statusSubscriptions.clear();
		}
	},
	actions: {
		async connectMessenger({ commit, state, rootGetters }) {
			try {
				// Закрываем предыдущее соединение
				if (state.socket) {
					state.socket.close();
					commit('SET_SOCKET', null);
					commit('SET_CONNECTION_STATUS', false);
				}

				const token = localStorage.getItem('access_token');
				if (!token) {
					throw new Error('Токен не найден');
				}

				const wsServerUrl = import.meta.env.VITE_API_WS_SERVER_URL || 'ws://localhost:9000';
				const socket = new WebSocket(`${wsServerUrl}/ws/${token}/messenger`);

				commit('SET_SOCKET', socket);

				socket.onopen = () => {
					console.log('Messenger WebSocket соединение установлено');
					commit('SET_CONNECTION_STATUS', true);
				};

				socket.onclose = (event) => {
					console.log('Messenger WebSocket соединение закрыто', event);
					commit('SET_CONNECTION_STATUS', false);
				};

				socket.onerror = (error) => {
					console.error('Messenger WebSocket ошибка:', error);
					commit('SET_CONNECTION_STATUS', false);
				};

				socket.onmessage = (event) => {
					try {
						const data = JSON.parse(event.data);
						this.dispatch('messenger/handleMessengerMessage', data);
					} catch (error) {
						console.error('Ошибка обработки сообщения мессенджера:', error);
					}
				};

			} catch (error) {
				console.error('Ошибка подключения Messenger WebSocket:', error);
				commit('SET_CONNECTION_STATUS', false);
				throw error;
			}
		},

		disconnectMessenger({ commit, state }) {
			if (state.socket) {
				state.socket.close();
				commit('SET_SOCKET', null);
				commit('SET_CONNECTION_STATUS', false);
			}
		},

		handleMessengerMessage({ commit, rootGetters }, data) {
			const currentUser = rootGetters['getUser'];

			switch (data.type) {
				case 'private_message':
					const isFromCurrentUser = data.sender_uid === currentUser.uid;
					const otherUserId = isFromCurrentUser ? data.receiver_uid : data.sender_uid;

					commit('ADD_MESSAGE', {
						userId: otherUserId,
						message: {
							...data,
							isCurrentUser: isFromCurrentUser,
							timestamp: new Date(data.created_at),
						},
					});

					if (!isFromCurrentUser) {
						this.dispatch('messenger/playNotificationSound');
					}
					break;

				case 'message_read':
					// Обработка отметки о прочтении
					commit('MARK_MESSAGE_AS_READ', data.message_id);
					break;

				case 'conversation':
					// Загрузка истории переписки
					commit('SET_CONVERSATION', {
						userId: data.other_user_uid,
						messages: data.messages.reverse().map(msg => ({
							...msg,
							isCurrentUser: msg.sender_uid === currentUser.uid,
							timestamp: new Date(msg.created_at)
						}))
					});
					break;

				case 'status_update':
					Object.entries(data.statuses).forEach(([userId, isOnline]) => {
						commit('UPDATE_ONLINE_STATUS', { userId, isOnline });
					});
					break;

				default:
					console.warn('Неизвестный тип сообщения мессенджера:', data.type);
			}
		},

		setActiveDialog({ commit }, userId) {
			commit('SET_ACTIVE_DIALOG', userId);
		},

		sendPrivateMessage({ state }, messageData) {
			if (state.socket && state.socket.readyState === WebSocket.OPEN) {
				state.socket.send(JSON.stringify({
					action: 'send_message',
					...messageData
				}));
			} else {
				throw new Error('Messenger WebSocket не подключен');
			}
		},

		requestConversation({ state }, { otherUserId, requestId }) {
			if (state.socket && state.socket.readyState === WebSocket.OPEN) {
				state.socket.send(JSON.stringify({
					action: 'get_conversation',
					other_user_uid: otherUserId,
					request_id: requestId,
				}));
			}
		},
		markMessageAsRead({ state, commit }, messageId) {
			if (state.socket && state.socket.readyState === WebSocket.OPEN) {
				// Отправляем запрос на сервер через WebSocket
				state.socket.send(JSON.stringify({
					action: 'mark_message_as_read',
					message_uid: messageId,
				}));
			} else {
				// Если WebSocket не подключен, сохраняем запрос в очередь
				console.warn('WebSocket не подключен. Добавляем запрос в очередь...');
				commit('ADD_PENDING_READ_REQUEST', messageId);
			}
		},
		playNotificationSound() {
			const audio = new Audio('/sounds/private_notification.mp3');
			audio.preload = 'auto';

			audio.addEventListener('canplaythrough', () => {
				audio.play().catch((e) => {
					console.error('Ошибка воспроизведения звука:', e);
				});
			});

			audio.addEventListener('error', (e) => {
				console.error('Ошибка загрузки аудио:', e);
			});

			audio.load();
		},

		clearNotifications({ commit }) {
			commit('CLEAR_NOTIFICATIONS');
		},
		subscribeToStatuses({ commit, state }, userIds) {
			if (state.socket?.readyState === WebSocket.OPEN) {
				state.socket.send(JSON.stringify({
					action: 'subscribe_status',
					userIds: Array.from(userIds)
				}));
				commit('UPDATE_STATUS_SUBSCRIPTIONS', { userIds, subscribe: true });
			}
		},

		// Отписка от статусов
		unsubscribeFromStatuses({ commit, state }, userIds) {
			if (state.socket?.readyState === WebSocket.OPEN) {
				state.socket.send(JSON.stringify({
					action: 'unsubscribe_status',
					userIds: Array.from(userIds)
				}));
				commit('UPDATE_STATUS_SUBSCRIPTIONS', { userIds, subscribe: false });
			}
		},

		// При подключении восстанавливаем подписки
		restoreStatusSubscriptions({ state, dispatch }) {
			if (state.statusSubscriptions.size > 0) {
				dispatch('subscribeToStatuses', [...state.statusSubscriptions]);
			}
		}
	}
};