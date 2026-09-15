import $api from '.';

const withUtc = (promise) => promise.then((response) => {
	const normalize = (value, key = '') => {
		if (Array.isArray(value)) return value.map((item) => normalize(item));
		if (value && typeof value === 'object') {
			return Object.fromEntries(Object.entries(value).map(([childKey, childValue]) => [childKey, normalize(childValue, childKey)]));
		}
		if (typeof value === 'string' && key.endsWith('_at') && !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return `${value}Z`;
		return value;
	};
	response.data = normalize(response.data);
	return response;
});

export default class EngagementService {
	static myPersonaAppearance() {
		return withUtc($api.get('/appearance/v1/me/persona'));
	}

	static updateMyPersonaAppearance(payload) {
		return withUtc($api.patch('/appearance/v1/me/persona', payload));
	}

	static personaAppearance(personaUid) {
		return withUtc($api.get(`/appearance/v1/personas/${personaUid}`));
	}

	static spaceAppearance(spaceUid) {
		return withUtc($api.get(`/appearance/v1/spaces/${spaceUid}`));
	}

	static updateSpaceAppearance(spaceUid, payload) {
		return withUtc($api.patch(`/appearance/v1/spaces/${spaceUid}`, payload));
	}

	static activities(spaceUid, params = {}) {
		return withUtc($api.get(`/activities/v1/spaces/${spaceUid}`, { params }));
	}

	static createActivity(spaceUid, payload) {
		return withUtc($api.post(`/activities/v1/spaces/${spaceUid}`, payload));
	}

	static updateActivity(spaceUid, activityUid, payload) {
		return withUtc($api.patch(`/activities/v1/spaces/${spaceUid}/${activityUid}`, payload));
	}

	static rsvp(activityUid, status) {
		return withUtc($api.put(`/activities/v1/${activityUid}/rsvp`, { status }));
	}

	static clearRsvp(activityUid) {
		return withUtc($api.delete(`/activities/v1/${activityUid}/rsvp`));
	}
}
