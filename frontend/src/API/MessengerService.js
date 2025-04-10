import $api from ".";
import CSRFService from './CSRFService';

export default {
	async getConversations() {
		//await CSRFService.getCSRF();
		return $api.get('/api/messenger/conversations');
	},

	async getConversation(userId) {
		//await CSRFService.getCSRF();
		return $api.get(`/api/messenger/conversations/${userId}`);
	},

	async searchUsers(query) {
		//await CSRFService.getCSRF();
		return $api.get('/api/messenger/search', { params: { q: query } });
	}
};