import axios from "axios";
import store from "@/stores";

const $api = axios.create({
    withCredentials: true, // Включаем отправку кук
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000', // Базовый URL вашего API
});

let isRefreshing = false; // Флаг для предотвращения множественных запросов на обновление токена
let failedQueue = []; // Очередь для хранения запросов, ожидающих обновления токена

// Функция для обработки очереди запросов
const processQueue = (error = null) => {
    failedQueue.forEach((callback) => callback(error));
    failedQueue = [];
};

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

// Перехватчик ответов: обработка ошибок
$api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // Обработка ошибки 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._isRetry) {
            if (!isRefreshing) {
                isRefreshing = true;
                originalRequest._isRetry = true;

                try {
                    // Обновляем токен
                    const refreshResponse = await axios.get(`${$api.defaults.baseURL}/refresh`, {
                        withCredentials: true,
                    });
                    const { access_token } = refreshResponse.data;

                    // Сохраняем новый access_token
                    localStorage.setItem('access_token', access_token);

                    // Устанавливаем новый токен в заголовки
                    originalRequest.headers.Authorization = `Bearer ${access_token}`;

                    // Повторяем все запросы из очереди
                    processQueue();

                    // Повторяем исходный запрос и возвращаем его результат
                    return $api(originalRequest);
                } catch (refreshError) {
                    // Если обновление токена не удалось, очищаем данные и перенаправляем на страницу входа
                    processQueue(refreshError);
                    localStorage.clear();
                    store.dispatch('clearUser');
                    window.location.href = '/login';
                    return Promise.reject(refreshError);
                } finally {
                    isRefreshing = false;
                }
            } else {
                // Добавляем запрос в очередь на повторение
                return new Promise((resolve, reject) => {
                    failedQueue.push((err) => {
                        if (err) {
                            reject(err);
                        } else {
                            resolve($api(originalRequest));
                        }
                    });
                });
            }
        }

        // Обработка ошибки 403 Forbidden
        if (error.response?.status === 403) {
            console.error('Доступ запрещен: токен недействителен или удален.');

            // Очищаем данные аутентификации
            localStorage.clear();
            store.dispatch('clearUser');

            // Перенаправляем пользователя на страницу входа
            if (!window.location.pathname.includes('/login')) {
                window.location.href = '/login';
            }

            // Прерываем выполнение
            throw error;
        }

        // Обработка других ошибок
        if (error.response?.status === 400) {
            console.error('Ошибка валидации:', error);
        }

        // Пробрасываем ошибку дальше
        throw error;
    }
);

export default $api;