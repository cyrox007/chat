import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import store from './stores';
import { registerPubChatServiceWorker } from '@/pwa/registerServiceWorker';

import "@/assets/main.css";
import "@/assets/ui-utilities.css";
import "@/assets/messaging-ux.css";

const app = createApp(App);

app.use(store);
app.use(router);

app.mount('#app');

window.addEventListener('pubchat:account-access-restricted', () => {
	if (router.currentRoute.value.name !== 'restricted-safety') {
		router.replace({ name: 'restricted-safety' }).catch(() => null);
	}
});

registerPubChatServiceWorker();
