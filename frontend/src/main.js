import { createApp } from 'vue'
import { createPinia } from 'pinia'

/* import "@/assets/fa/css/all.css"; */
import "@/assets/main.css";

import App from './App.vue'
import router from './router'
import store from './stores/user';

const app = createApp(App)

app.use(createPinia())
app.use(store);
app.use(router)

app.mount('#app')
