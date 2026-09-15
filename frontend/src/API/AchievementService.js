import $api from '.';

export default class AchievementService {
	static mine(params = {}) {
		return $api.get('/achievements/v1/me', { params });
	}

	static publicForAccount(accountUid, params = {}) {
		return $api.get(`/achievements/v1/accounts/${accountUid}`, { params });
	}
}
