import axios from "axios";
import store from "@/stores";

const $api = axios.create({
	withCredentials: true, // Включаем отправку кук
	baseURL: import.meta.env.VITE_API_BASE_URL, // Базовый URL вашего API
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
$api.interceptors.response.use(
	(config) => {
		return config;
	},
	async (error) => {
		const originalRequest = error.config;

		// Обработка ошибки 401 Unauthorized
		if (error.response?.status === 401 && !originalRequest._isRetry) {
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

				// Повторяем исходный запрос
				return $api.request(originalRequest);
			} catch (e) {
				// Если обновление токена не удалось, очищаем данные и перенаправляем на страницу входа
				localStorage.clear();
				store.dispatch('clearUser');
				window.location.href = '/login';
			}
		}

		// Обработка ошибки 403 Forbidden
		if (error.response?.status === 403) {
			console.error('Доступ запрещен: токен недействителен или удален.');

			// Очищаем данные аутентификации
			localStorage.clear();
			store.dispatch('clearUser');

			// Перенаправляем пользователя на страницу входа
			window.location.href = '/login';

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