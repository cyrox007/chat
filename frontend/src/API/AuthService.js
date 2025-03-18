import $api from ".";

export default class AuthService {
    static async registration(data) {
        return $api.post('/auth/registration', data);
    }
    static async login(data) {
        return $api.post('/users/login', data);
    }
    static async logout() {
        return $api.get('/users/logout');
    }
    // Другие методы...
}