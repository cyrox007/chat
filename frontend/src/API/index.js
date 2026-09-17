import axios from "axios";
import store from "@/stores";
import { clearAccessToken, getAccessToken, setAccessToken } from "@/API/session";

const $api = axios.create({
    withCredentials: true,
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000',
});

let isRefreshing = false;
let failedQueue = [];

const clearSessionStorage = () => {
    clearAccessToken();
    localStorage.removeItem('auth');
    localStorage.removeItem('user');
    localStorage.removeItem('identity');
    // Remove bearer tokens left by pre-Realtime-v2 builds.
    localStorage.removeItem('access_token');
};

const expireSession = () => {
    clearSessionStorage();
    store.dispatch('clearUser');
    window.dispatchEvent(new CustomEvent('pubchat:session-expired'));
};

const ensureCsrfCookie = async () => {
    await axios.get(`${$api.defaults.baseURL}/csrf/get`, { withCredentials: true });
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
    const accessToken = getAccessToken();
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
        const detail = error.response?.data?.detail;
        const isIdentityRefresh = originalRequest?.url?.includes('/identity/v2/refresh');
        const isCsrfFailure = status === 403 && typeof detail === 'string' && detail.includes('CSRF');
        const isAccountAccessRestriction = (
            status === 403
            && detail
            && typeof detail === 'object'
            && detail.error_type === 'account_access_restricted'
        );

        if (isAccountAccessRestriction) {
            store.commit('setAccessRestriction', detail.restriction || null);
            window.dispatchEvent(new CustomEvent('pubchat:account-access-restricted'));
            return Promise.reject(error);
        }

        if (isCsrfFailure && !originalRequest?._csrfRetry) {
            originalRequest._csrfRetry = true;
            try {
                await ensureCsrfCookie();
                return $api(originalRequest);
            } catch (csrfError) {
                return Promise.reject(csrfError);
            }
        }

        if (status === 401 && !originalRequest?._isRetry && !isIdentityRefresh) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject, request: originalRequest });
                });
            }

            isRefreshing = true;
            originalRequest._isRetry = true;

            try {
                await ensureCsrfCookie();
                const refreshResponse = await axios.post(
                    `${$api.defaults.baseURL}/identity/v2/refresh`,
                    {},
                    { withCredentials: true }
                );
                const accessToken = refreshResponse.data.access_token;
                setAccessToken(accessToken);
                if (refreshResponse.data.access_restriction) {
                    store.commit('setAccessRestriction', refreshResponse.data.access_restriction);
                    window.dispatchEvent(new CustomEvent('pubchat:account-access-restricted'));
                }
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

        // 403 is an authorization decision, not an expired session.
        return Promise.reject(error);
    }
);

export default $api;
