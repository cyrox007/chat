export class WebSocketService {
    constructor(roomId, token) {
        this.roomId = roomId;
        this.token = token;
        this.socket = null;
    }

    connect() {
        this.socket = new WebSocket(`ws://localhost:9001/ws/${this.token}/rooms/${this.roomId}`);
        return this.socket;
    }

    send(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(message);
        } else {
            console.error('WebSocket не готов для отправки сообщений');
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}