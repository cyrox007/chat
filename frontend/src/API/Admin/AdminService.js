import $api from '@/API';

export default class AdminService {
	static async getDashboardStats() {
		return $api.get('/admin/dashboard/stats');
	}

	static async getOnlineUsers() {
		return $api.get('/admin/users/online');
	}

	static async getRoomStats() {
		return $api.get('/admin/rooms/stats');
	}
}