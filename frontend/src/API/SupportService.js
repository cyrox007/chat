import $api from '.';

const normalizeUtc = (promise) => promise.then((response) => {
	const visit = (value, key = '') => {
		if (Array.isArray(value)) return value.map((item) => visit(item));
		if (value && typeof value === 'object') {
			return Object.fromEntries(Object.entries(value).map(([childKey, childValue]) => [childKey, visit(childValue, childKey)]));
		}
		if (typeof value === 'string' && key.endsWith('_at') && !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return `${value}Z`;
		return value;
	};
	response.data = visit(response.data);
	return response;
});

export default class SupportService {
	static catalog(target = 'persona') { return $api.get('/support/v1/catalog', { params: { target } }); }
	static myProfile() { return $api.get('/support/v1/me/profile'); }
	static updateMyProfile(payload) { return $api.patch('/support/v1/me/profile', payload); }
	static myReceived(params = {}) { return normalizeUtc($api.get('/support/v1/me/received', { params })); }
	static personaShelf(personaUid) { return $api.get(`/support/v1/personas/${personaUid}/shelf`); }
	static giftPersona(personaUid, payload) { return normalizeUtc($api.post(`/support/v1/personas/${personaUid}/gifts`, payload)); }
	static spaceSettings(spaceUid) { return $api.get(`/support/v1/spaces/${spaceUid}/settings`); }
	static updateSpaceSettings(spaceUid, payload) { return $api.patch(`/support/v1/spaces/${spaceUid}/settings`, payload); }
	static spaceShelf(spaceUid) { return $api.get(`/support/v1/spaces/${spaceUid}/shelf`); }
	static giftSpace(spaceUid, payload) { return normalizeUtc($api.post(`/support/v1/spaces/${spaceUid}/gifts`, payload)); }
	static spaceReceived(spaceUid, params = {}) { return normalizeUtc($api.get(`/support/v1/spaces/${spaceUid}/received`, { params })); }
}
