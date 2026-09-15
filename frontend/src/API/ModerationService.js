import $api from '.';

export default class ModerationService {
	static myReports(params = {}) {
		return $api.get('/moderation/v1/me/reports', { params });
	}

	static myActions(params = {}) {
		return $api.get('/moderation/v1/me/actions', { params });
	}

	static myAppeals(params = {}) {
		return $api.get('/moderation/v1/me/appeals', { params });
	}

	static appeal(actionUid, body) {
		return $api.post(`/moderation/v1/actions/${actionUid}/appeals`, { body });
	}

	static createReport(spaceUid, payload) {
		return $api.post(`/moderation/v1/spaces/${spaceUid}/reports`, payload);
	}

	static reports(spaceUid, params = {}) {
		return $api.get(`/moderation/v1/spaces/${spaceUid}/reports`, { params });
	}

	static updateReport(spaceUid, reportUid, status) {
		return $api.patch(`/moderation/v1/spaces/${spaceUid}/reports/${reportUid}`, { status });
	}

	static createAction(spaceUid, payload) {
		return $api.post(`/moderation/v1/spaces/${spaceUid}/actions`, payload);
	}

	static actions(spaceUid, params = {}) {
		return $api.get(`/moderation/v1/spaces/${spaceUid}/actions`, { params });
	}

	static appeals(spaceUid, params = {}) {
		return $api.get(`/moderation/v1/spaces/${spaceUid}/appeals`, { params });
	}

	static resolveAppeal(spaceUid, appealUid, payload) {
		return $api.patch(`/moderation/v1/spaces/${spaceUid}/appeals/${appealUid}`, payload);
	}
}
