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

export default class NotificationService {
	static sync() {
		return withUtc($api.post('/notifications/v1/sync'));
	}

	static list(params = {}) {
		return withUtc($api.get('/notifications/v1', { params }));
	}

	static unreadCount() {
		return $api.get('/notifications/v1/unread-count');
	}

	static messagePreferences() {
		return $api.get('/notifications/v1/message-preferences');
	}

	static updateMessagePreferences(payload) {
		return $api.patch('/notifications/v1/message-preferences', payload);
	}

	static remindersForSpace(spaceUid) {
		return withUtc($api.get(`/notifications/v1/spaces/${spaceUid}/reminders`));
	}

	static setReminder(activityUid, leadMinutes) {
		return withUtc($api.put(`/notifications/v1/activities/${activityUid}/reminder`, { lead_minutes: leadMinutes }));
	}

	static clearReminder(activityUid) {
		return $api.delete(`/notifications/v1/activities/${activityUid}/reminder`);
	}

	static markRead(notificationUid) {
		return withUtc($api.patch(`/notifications/v1/${notificationUid}/read`));
	}

	static markAllRead() {
		return $api.post('/notifications/v1/read-all');
	}

	static occurrences(activityUid, params = {}) {
		return withUtc($api.get(`/activity-occurrences/v1/activities/${activityUid}`, { params }));
	}
}
