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

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}