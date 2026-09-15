import axios from "axios";
import store from "@/stores";

const $api = axios.create({
    withCredentials: true,
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000',
});

let isRefreshing = false;
let failedQueue = [];

const clearSessionStorage = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('auth');
    localStorage.removeItem('user');
    localStorage.removeItem('identity');
};

const expireSession = () => {
    clearSessionStorage();
    store.dispatch('clearUser');
    window.dispatchEvent(new CustomEvent('pubchat:session-expired'));
};

const processQueue = (error = null, accessToken = null) => {
    failedQueue.forEach(({ resolve, reject, request }) => {
        if (error) {
            reject(error);
            return;
        }
        request.headers.Authorization = `Bearer ${accessToken}`;
        resolve($api(request));
    });
    failedQueue = [];
};

$api.interceptors.request.use((config) => {
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
});

$api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        const status = error.response?.status;
        const isIdentityRefresh = originalRequest?.url?.includes('/identity/v2/refresh');

        if (status === 401 && !originalRequest?._isRetry && !isIdentityRefresh) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject, request: originalRequest });
                });
            }

            isRefreshing = true;
            originalRequest._isRetry = true;

            try {
                const refreshResponse = await axios.post(
                    `${$api.defaults.baseURL}/identity/v2/refresh`,
                    {},
                    { withCredentials: true }
                );
                const accessToken = refreshResponse.data.access_token;
                localStorage.setItem('access_token', accessToken);
                originalRequest.headers.Authorization = `Bearer ${accessToken}`;
                processQueue(null, accessToken);
                return $api(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError);
                expireSession();
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        // 403 means "authenticated but not allowed". It must never silently log
        // a user out (e.g. opening an admin-only screen as a normal member).
        return Promise.reject(error);
    }
);

export default $api;
