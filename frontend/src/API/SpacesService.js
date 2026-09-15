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

	static members(spaceUid, params = {}) {
		return $api.get(`/spaces/v1/${spaceUid}/members`, { params });
	}

	static updateMemberRole(spaceUid, accountUid, role) {
		return $api.patch(`/spaces/v1/${spaceUid}/members/${accountUid}`, { role });
	}

	static manageMembership(spaceUid, accountUid, action) {
		return $api.patch(`/spaces/v1/${spaceUid}/members/${accountUid}/membership`, { action });
	}

	static invite(spaceUid, accountUid) {
		return $api.post(`/spaces/v1/${spaceUid}/invitations/${accountUid}`);
	}

	static revokeInvitation(spaceUid, accountUid) {
		return $api.delete(`/spaces/v1/${spaceUid}/invitations/${accountUid}`);
	}

	static invitations(params = {}) {
		return $api.get('/spaces/v1/invitations', { params });
	}

	static respondInvitation(invitationUid, action) {
		return $api.patch(`/spaces/v1/invitations/${invitationUid}`, { action });
	}

	static rules(spaceUid) {
		return $api.get(`/spaces/v1/${spaceUid}/rules`);
	}

	static createRule(spaceUid, payload) {
		return $api.post(`/spaces/v1/${spaceUid}/rules`, payload);
	}

	static updateRule(spaceUid, ruleUid, payload) {
		return $api.patch(`/spaces/v1/${spaceUid}/rules/${ruleUid}`, payload);
	}

	static deleteRule(spaceUid, ruleUid) {
		return $api.delete(`/spaces/v1/${spaceUid}/rules/${ruleUid}`);
	}

	static events(spaceUid, params = {}) {
		return $api.get(`/spaces/v1/${spaceUid}/events`, { params });
	}

	static createEvent(spaceUid, payload) {
		return $api.post(`/spaces/v1/${spaceUid}/events`, payload);
	}

	static updateEvent(spaceUid, eventUid, payload) {
		return $api.patch(`/spaces/v1/${spaceUid}/events/${eventUid}`, payload);
	}

	static deleteEvent(spaceUid, eventUid) {
		return $api.delete(`/spaces/v1/${spaceUid}/events/${eventUid}`);
	}

	static history(spaceUid, params = {}) {
		return $api.get(`/spaces/v1/${spaceUid}/history`, { params });
	}
}
