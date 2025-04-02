import { createStore } from 'vuex';
import userStore from './user';
import chatStore from './chat';

export default createStore({
	modules: {
		user: userStore,
		chat: chatStore,
	},
});