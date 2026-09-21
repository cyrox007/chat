import $api, { API_BASE_URL } from '.';

const websocketBaseUrl = () => {
    const configured = import.meta.env.VITE_API_WS_SERVER_URL;
    if (configured) return configured.replace(/\/$/, '');

    if (/^https?:\/\//i.test(API_BASE_URL)) {
        return API_BASE_URL.replace(/^http/i, 'ws').replace(/\/$/, '');
    }

    const origin = window.location.origin.replace(/^http/i, 'ws').replace(/\/$/, '');
    const relativeBase = API_BASE_URL.startsWith('/') ? API_BASE_URL : `/${API_BASE_URL}`;
    return `${origin}${relativeBase}`.replace(/\/$/, '');
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
