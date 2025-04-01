<template>
	<div class="login-container">
		<div class="login-form">
			<h1>Авторизация</h1>
			<form @submit.prevent="handleLogin">
				<div class="form-group">
					<label for="identifier">Логин / Email / Телефон:</label>
					<input type="text" id="identifier" v-model="identifier" required
						placeholder="Введите логин, email или телефон" />
				</div>
				<div class="form-group">
					<label for="password">Пароль:</label>
					<input type="password" id="password" v-model="password" required placeholder="Введите пароль"
						autocomplete="off" @copy.prevent @paste.prevent />
				</div>
				<button type="submit" class="btn-primary">Войти</button>
				<p v-if="errorMessage" class="error">{{ errorMessage }}</p>
			</form>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useStore } from 'vuex';
import CSRFService from '@/API/CSRFService';
import AuthService from '@/API/AuthService';
import DOMPurify from 'dompurify'; // Для защиты от XSS

// Реактивные переменные
const identifier = ref('');
const password = ref('');
const errorMessage = ref('');

const store = useStore();

// Запрос CSRF-токена при загрузке страницы
onMounted(async () => {
	try {
		await fetchCSRFToken();
	} catch (error) {
		console.error('Failed to fetch CSRF token:', error);
	}
});

// Функция для запроса CSRF-токена
const fetchCSRFToken = async () => {
	await CSRFService.getCSRF(); // Запрос на получение CSRF-токена
};

// Функция для валидации ввода
const validateInput = (value) => {
	const sanitizedValue = DOMPurify.sanitize(value); // Экранируем ввод для защиты от XSS

	// Проверяем, что значение содержит только разрешенные символы
	const allowedCharsRegex = /^[a-zA-Z0-9@.+_-]+$/; // Разрешаем буквы, цифры, @, ., +, -, _
	if (!allowedCharsRegex.test(sanitizedValue)) {
		throw new Error('Недопустимые символы в поле ввода');
	}

	return sanitizedValue;
};

// Обработчик входа
const handleLogin = async () => {
	try {
		// Валидируем и очищаем ввод
		const sanitizedIdentifier = validateInput(identifier.value);

		const response = await AuthService.login({
			identifier: sanitizedIdentifier,
			password: password.value,
		});

		// Сохраняем токен в localStorage
		localStorage.setItem('access_token', response.data.access_token);

		// Сохраняем данные пользователя в хранилище
		store.commit('setUser', response.data.user);
		store.commit('setAuth', true);

		// Очищаем форму
		identifier.value = '';
		password.value = '';

		// Перенаправляем на главную страницу
		window.location.href = '/';
	} catch (error) {
		errorMessage.value = error.response?.data?.message || 'Ошибка входа';
	}
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

.login-form h1 {
	text-align: center;
}

form {
	margin-top: 20px;
	width: 100%;
}

.form-group {
	margin-bottom: 15px;
	width: 100%;
	/* display: flex;
    flex-direction: column; */
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

/* .btn-primary:hover {
    background: darken(var(--primary-color), 10%);
} */

.error {
	color: red;
	margin-top: 10px;
}
</style>