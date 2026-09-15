import $api from '.';

export default class SpacesService {
	static list(params = {}) {
		return $api.get('/spaces/v1', { params });
	}

	static get(spaceUid) {
		return $api.get(`/spaces/v1/${spaceUid}`);
	}

	static create(payload) {
		return $api.post('/spaces/v1', payload);
	}

	static update(spaceUid, payload) {
		return $api.patch(`/spaces/v1/${spaceUid}`, payload);
	}

	static archive(spaceUid) {
		return $api.delete(`/spaces/v1/${spaceUid}`);
	}

	static join(spaceUid) {
		return $api.post(`/spaces/v1/${spaceUid}/join`);
	}

	static leave(spaceUid) {
		return $api.delete(`/spaces/v1/${spaceUid}/membership`);
	}

	static members(spaceUid) {
		return $api.get(`/spaces/v1/${spaceUid}/members`);
	}

	static updateMemberRole(spaceUid, accountUid, role) {
		return $api.patch(`/spaces/v1/${spaceUid}/members/${accountUid}`, { role });
	}
}
