// src/composables/useWebSocket.js
/* import { ref } from 'vue';
import { WebSocketService } from '@/services/WebSocketService';

export function useWebSocket(roomId) {
    const messages = ref([]);
    const connectedUsers = ref([]);
    const socket = ref(null);

    const connect = (token) => {
        const wsService = new WebSocketService(roomId, token);
        socket.value = wsService.connect();

        socket.value.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                messages.value.push(data.message);
            } else if (data.type === 'user_list') {
                connectedUsers.value = data.users;
            }
        };

        socket.value.onclose = () => {
            console.log('WebSocket соединение закрыто');
        };
    };

    const disconnect = () => {
        if (socket.value) {
            socket.value.close();
        }
    };

    return { messages, connectedUsers, connect, disconnect };
} */