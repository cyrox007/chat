import axios from "axios";

const $api = axios.create({
    withCredentials: true, // Включаем отправку кук
    baseURL: 'http://localhost:9001', // Базовый URL вашего API
});

// Перехватчик запросов: добавляем токен в заголовки
$api.interceptors.request.use((config) => {
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// Перехватчик ответов: обработка ошибок 401
$api.interceptors.response.use((config) => {
    return config;
}, async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && originalRequest && !originalRequest._isRetry) {
        originalRequest._isRetry = true;
        try {
            await store.dispatch('refreshToken'); // Обновляем токен через Vuex
            return $api.request(originalRequest); // Повторяем оригинальный запрос
        } catch (e) {
            localStorage.clear();
            store.commit('setAuth', false); // Обновляем состояние аутентификации
            window.location.href = "/login"; // Перенаправляем на страницу входа
        }
    }

    if (error.response?.status === 400) {
        console.error(error);
    }
    throw error;
});

export default $api;