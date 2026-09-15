import $api from '.';

const websocketBaseUrl = () => {
    const configured = import.meta.env.VITE_API_WS_SERVER_URL;
    if (configured) return configured.replace(/\/$/, '');

    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';
    return apiBase.replace(/^http/i, 'ws').replace(/\/$/, '');
};

export default class RealtimeService {
    static async createTicket(target, roomUid = null) {
        const payload = { target };
        if (roomUid) payload.room_uid = roomUid;
        return $api.post('/realtime/v2/tickets', payload);
    }

    static openSocket(websocketPath) {
        return new WebSocket(`${websocketBaseUrl()}${websocketPath}`);
    }

    static async prepareSocket(target, roomUid = null) {
        const response = await this.createTicket(target, roomUid);
        return {
            socket: this.openSocket(response.data.websocket_path),
            ticket: response.data.ticket,
            expiresIn: response.data.expires_in,
            protocol: response.data.protocol,
        };
    }
}
