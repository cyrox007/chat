<template>
    <div class="login-container" >
        <div class="login-form">
            <h1>Авторизация</h1>
            <form @submit.prevent="handleLogin">
                <div class="form-group">
                    <label for="username">Логин:</label>
                    <input type="text" id="username" v-model="username" required />
                </div>
                <div class="form-group">
                    <label for="password">Пароль:</label>
                    <input type="password" id="password" v-model="password" required />
                </div>
                <button type="submit" class="btn-primary">Войти</button>
                <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
            </form>
        </div>
    </div>
</template>

<script>
import { ref } from 'vue';
import AuthService from '@/API/AuthService'; // Импортируем AuthService

export default {
    setup() {
        const username = ref('');
        const password = ref('');
        const errorMessage = ref('');

        const handleLogin = async () => {
            try {
                const response = await AuthService.login({
                    username: username.value,
                    password: password.value,
                });

                // Предполагаем, что токен возвращается в ответе
                localStorage.setItem('access_token', response.data.access_token);
                window.location.href = '/'; // Перенаправление на главную страницу
            } catch (error) {
                errorMessage.value = error.response?.data?.message || 'Ошибка входа';
            }
        };

        return {
            username,
            password,
            errorMessage,
            handleLogin,
        };
    },
};
</script>

<style scoped>
/* Стили остаются прежними */
.login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    /* height: 100vh;
    background: var(--bg-gradient); */
    margin: 0 auto;
}

.login-form {
    background: var(--sidebar-bg-light);
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    width: 100%;
    max-width: 400px;
}

.form-group {
    margin-bottom: 15px;
}

input[type="text"],
input[type="password"] {
    width: 100%;
    padding: 10px;
    border: 1px solid var(--primary-color);
    border-radius: 4px;
    background: #fff;
    /* color: var(--text-dark); */
}

input[type="text"]:focus,
input[type="password"]:focus {
    outline: none;
    border-color: var(--primary-color);
}

.btn-primary {
    background: var(--primary-color);
    color: #fff;
    padding: 10px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    width: 100%;
}

.btn-primary:hover {
    /* background: darken(var(--primary-color), 10%); */
}

.error {
    color: red;
    margin-top: 10px;
}
</style>
