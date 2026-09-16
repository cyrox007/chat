import { createStore } from 'vuex';
import userStore from './user';
import chatStore from './chat';
import messengerStore from './messenger';
import notificationsStore from './notifications';

export default createStore({
	modules: {
		user: userStore,
		chat: chatStore,
		messenger: messengerStore,
		notifications: notificationsStore,
	},
});
