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
$api.interceptors.response.use(
	(response) => response,
	async (error) => {
		const originalRequest = error.config;

		// Обработка ошибки 401 (токен истёк)
		if (error.response?.status === 401 && !originalRequest._isRetry) {
			originalRequest._isRetry = true;

			try {
				const refreshResponse = await axios.get(`${$api.defaults.baseURL}/refresh`, {
					withCredentials: true,
				});

				const { access_token } = refreshResponse.data;
				localStorage.setItem('access_token', access_token);

				originalRequest.headers.Authorization = `Bearer ${access_token}`;
				return $api(originalRequest);
			} catch (refreshError) {
				localStorage.clear();
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
);

export default $api;