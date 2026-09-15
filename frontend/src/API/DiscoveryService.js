import $api from '.';

const hasTimezone = (value) => /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);

const normalizeUtcTimestamps = (value, key = '') => {
	if (Array.isArray(value)) return value.map((item) => normalizeUtcTimestamps(item));
	if (value && typeof value === 'object') {
		return Object.fromEntries(
			Object.entries(value).map(([childKey, childValue]) => [childKey, normalizeUtcTimestamps(childValue, childKey)]),
		);
	}
	if (typeof value === 'string' && key.endsWith('_at') && !hasTimezone(value)) return `${value}Z`;
	return value;
};

export default class DiscoveryService {
	static spaces(params = {}) {
		return $api.get('/discovery/v1/spaces', { params }).then((response) => {
			response.data = normalizeUtcTimestamps(response.data);
			return response;
		});
	}
}
