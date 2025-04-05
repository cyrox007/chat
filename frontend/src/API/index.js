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
            store.dispatch('clearUser');
            window.location.href = '/login';
        }
    }
    
    if (error.response.status === 400) {
        console.error(error);
    }
    throw error;
})

export default $api;