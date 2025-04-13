import $api from ".";

export default class MessengerService {
	static async getDialogs() {
		return await $api.get('/messenger/dialogs');
	}
	/* async searchUsers(query) {
		//await CSRFService.getCSRF();
		return $api.get('/api/messenger/search', { params: { q: query } });
	} */
};