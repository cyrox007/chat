import $api from ".";

export default class PenaltyService {
	static async assignPenalty(userUid, penaltyData) {
		return await $api.post(`/admin/penalties/assign`, {
			user_uid: userUid,
			penalty_type: penaltyData.type,
			expires_at: penaltyData.end_time_utc, // Время окончания в UTC
			reason: penaltyData.reason,
		});
	}
}