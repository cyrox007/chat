import axios from "axios";

//export const API_URL = config.server;

const $api = axios.create({
    withCredentials: true,
    baseURL: 'http://localhost:9001' // Значение по умолчанию
});

$api.interceptors.request.use((config)=>{
    config.headers.Authorization = `Bearer ${localStorage.getItem('token')}`;
    return config;
});

$api.interceptors.response.use((config) => {
    return config;
}, async (error) => {
    const originalRequest = error.config;
    if (error.response.status === 401 && originalRequest && !originalRequest._isRetry) {
        originalRequest._isRetry = true;
        try {
            await store.dispatch('refreshToken'); // Обновляем токен через Vuex
            return $api.request(originalRequest); // Повторяем оригинальный запрос
        } catch (e) {
            localStorage.clear();
            store.commit('setAuth', false); // Обновляем состояние аутентификации
            this.$router.push("/login"); // Перенаправляем на страницу входа
        }
    }

    if (error.response.status === 400) {
        console.error(error);
    }
    throw error;
});


export default $api;