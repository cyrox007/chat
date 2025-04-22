import $api from "@/API/index";

export default class ProfileService {
	static async getUsers(params = {}) {
		try {
			const response = await $api.get('/admin/users', { params });
			return {
				data: response.data.users,
				total: response.data.total
			};
		} catch (error) {
			console.error('Error fetching users:', error);
			throw error;
		}
	}
	static async getUserRooms(uid) {
		return await $api.get(`/admin/users/${uid}/rooms`);
	}
	static async getUserPenalties(uid) {
		return await $api.get(`/admin/users/${uid}/penalties`);
	}
	static async deletePenalty(id) {
		return await $api.delete(`/admin/penalties/${id}`)
	}
	static async updateAdminProfile(uid, data) {
		return await $api.put(`/admin/users/${uid}`, { data: data })
	}
}