import $api from "@/API/index";

export default class ProfileService {
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
		return await $api.put(`/admin/users/${uid}`, {data: data})
	}
}