import $api from '.';

export default class ConversationRoundService {
	static list(activityUid) {
		return $api.get(`/activities/v1/${activityUid}/rounds`);
	}

	static create(activityUid, payload) {
		return $api.post(`/activities/v1/${activityUid}/rounds`, payload);
	}

	static close(activityUid, roundUid) {
		return $api.patch(`/activities/v1/${activityUid}/rounds/${roundUid}`, { status: 'closed' });
	}

	static responses(roundUid, params = {}) {
		return $api.get(`/activities/v1/rounds/${roundUid}/responses`, { params });
	}

	static respond(roundUid, payload) {
		return $api.put(`/activities/v1/rounds/${roundUid}/response`, payload);
	}
}
