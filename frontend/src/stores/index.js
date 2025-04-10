import { createStore } from 'vuex';
import userStore from './user';
import chatStore from './chat';
import messengerStore from './messenger';

export default createStore({
	modules: {
		user: userStore,
		chat: chatStore,
		messenger: messengerStore,
	},
});