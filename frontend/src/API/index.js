import axios from "axios";
import store from "@/stores";

const $api = axios.create({
	withCredentials: true, // Включаем отправку кук
	baseURL: 'http://localhost:9000', // Базовый URL вашего API
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

// Перехватчик ответов: обработка ошибок
/* $api.interceptors.response.use(
	(response) => response,
	async (error) => {
		const originalRequest = error.config;

		// Обработка ошибки 401 (токен истёк)
		if (error.response?.status === 401 && !originalRequest._isRetry) {
			originalRequest._isRetry = true;

			try {
				// Обновляем токен
				const refreshResponse = await axios.get(`${$api.defaults.baseURL}/refresh`, {
					withCredentials: true,
				});

				const { access_token } = refreshResponse.data;
				localStorage.setItem('access_token', access_token);

				// Устанавливаем новый токен в заголовки
				originalRequest.headers.Authorization = `Bearer ${access_token}`;

				// Повторяем исходный запрос
				return $api(originalRequest);
			} catch (refreshError) {
				// Если обновление токена не удалось, очищаем состояние и перенаправляем на страницу входа
				localStorage.clear();
				store.commit('clearUser');
				window.location.href = '/login';
			}
		}

		// Обработка других ошибок
		if (error.response?.status === 403) {
			alert('Доступ запрещён.');
		} else if (error.response?.status === 500) {
			alert('Внутренняя ошибка сервера.');
		}

		return Promise.reject(error);
	}
); */

$api.interceptors.response.use((config)=>{
    return config;
}, async (error) => {
    const originalRequest = error.config;
    if (error.response.status === 401 && error.config && !error.config._isRetry) {
        originalRequest._isRetry = true;
        try {
			// Обновляем токен
            const refreshResponse = await axios.get(`${$api.defaults.baseURL}/refresh`, {
				withCredentials: true,
			});
            const { access_token } = refreshResponse.data;

			localStorage.setItem('access_token', access_token);

			// Устанавливаем новый токен в заголовки
			originalRequest.headers.Authorization = `Bearer ${access_token}`;
			
            return $api.request(originalRequest);

        } catch (e) {
            localStorage.clear();
            store.commit('clearUser');
            window.location.href = '/login';
        }
    }
    
    if (error.response.status === 400) {
        console.error(error);
    }
    throw error;
})

export default $api;