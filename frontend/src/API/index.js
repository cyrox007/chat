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
    (response) => {
        return response; // Просто возвращаем успешный ответ
    },
    async (error) => {
        const originalRequest = error.config;

        // Проверяем, что это ошибка 401 и запрос еще не был повторен
        if (error.response?.status === 401 && originalRequest && !originalRequest._isRetry) {
            originalRequest._isRetry = true; // Помечаем запрос как повторяемый

            try {
                // Запрос на обновление токенов
                const refreshResponse = await axios.get(`${$api.defaults.baseURL}/refresh`, {
                    withCredentials: true, // Отправляем куки
                });

                // Сохраняем новый access_token в localStorage
                const { access_token } = refreshResponse.data;
                // console.log(access_token);
                
                localStorage.setItem('access_token', access_token);

                // Добавляем новый токен в заголовки оригинального запроса
                originalRequest.headers.Authorization = `Bearer ${access_token}`;

                // Повторяем оригинальный запрос
                return $api(originalRequest);
            } catch (refreshError) {
                // Если обновление токена не удалось, очищаем данные и перенаправляем на страницу входа
                localStorage.clear();
                window.location.href = "/login";
            }
        }

        // Для других ошибок просто пробрасываем их дальше
        return Promise.reject(error);
    }
);

export default $api;