import $api from ".";

export default class AuthService {
	static async registration(data) {
		return $api.post('/users/registration', data);
	}
	static async login(data) {
		return $api.post('/users/login', data);
	}
	static async logout() {
		return $api.get('/users/logout');
	}
	static async checkUsername(username) {
		return $api.post('/users/check-username', { username });
	}
	static async checkEmail(email) {
		return $api.post('/users/check-email', { email });
	}
	static async checkPhone(phone) {
		return $api.post('/users/check-phone', { phone });
	}
	static async getValidAccessToken() {
		return $api.get(`/service/check-token`);
	}
	// Другие методы...
}