export class WebSocketService {
	constructor(roomId, token) {
		this.roomId = roomId;
		this.token = token;
		this.socket = null;
		this.messageHandlers = [];
	}

	connect() {
		if (this.socket) {
			console.warn('WebSocket уже подключен');
			return this.socket;
		}

		this.socket = new WebSocket(`ws://localhost:9000/ws/${this.token}/rooms/${this.roomId}`);

		// Обработка открытия соединения
		this.socket.onopen = () => {
			console.log('WebSocket подключен');
		};

		// Обработка входящих сообщений
		this.socket.onmessage = (event) => {
			const data = JSON.parse(event.data);
			this.messageHandlers.forEach((handler) => handler(data));
		};

		// Обработка ошибок
		this.socket.onerror = (error) => {
			console.error('WebSocket ошибка:', error);
		};

		// Обработка закрытия соединения
		this.socket.onclose = () => {
			console.log('WebSocket соединение закрыто');
			this.socket = null; // Очищаем ссылку на WebSocket
		};

		return this.socket;
	}

	// Метод для отправки сообщений
	send(message) {
		if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
			console.error('WebSocket не подключен или соединение закрыто');
			return;
		}
		this.socket.send(JSON.stringify(message));
	}

	// Метод для подписки на входящие сообщения
	onMessage(handler) {
		if (typeof handler !== 'function') {
			console.error('Handler должен быть функцией');
			return;
		}
		this.messageHandlers.push(handler);
	}

	// Метод для отключения WebSocket
	disconnect() {
		if (this.socket) {
			this.socket.close();
			this.socket = null;
		}
		this.messageHandlers = []; // Очищаем обработчики
	}
}