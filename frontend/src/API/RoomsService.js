import $api from ".";

export default class RoomsService {
    static async get_rooms() {
        return $api.get('/rooms/');
    }
}