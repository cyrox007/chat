import $api from ".";

export default class RoomsService {
    static async get_rooms() {
        return $api.get('/rooms/');
    }
    
    static async get_room(roomId) {
        return $api.get(`/rooms/${roomId}`);
    }
}