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
			<span>
				Еще не зарегистрированы?
				<a href="#" @click.prevent="goToRegistration">Регистрация</a>
			</span>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useStore } from 'vuex';
import CSRFService from '@/API/CSRFService';
import AuthService from '@/API/AuthService';
import DOMPurify from 'dompurify'; // Для защиты от XSS
import router from '@/router';

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
		const sanitizedIdentifier = validateInput(identifier.value);

		const response = await AuthService.login({
			identifier: sanitizedIdentifier,
			password: password.value,
		});

		if (response.data.status === 'ok') {
			// Сохраняем токен в localStorage
			localStorage.setItem('access_token', response.data.access_token);
			localStorage.setItem('user', JSON.stringify(response.data.user));

			// Сохраняем данные пользователя в хранилище
			store.commit('setUser', response.data.user);
			store.commit('setAuth', true);

			// Очищаем форму
			identifier.value = '';
			password.value = '';

			// Перенаправляем на главную страницу
			window.location.href = '/';
			return
		} else {
			errorMessage.value = response.data.message;
			return;
		}
	} catch (error) {
		errorMessage.value = error.response?.data?.message || 'Ошибка входа';
	}
};
const goToRegistration = () => {
	router.push({ name: 'registration' }); // Убедитесь, что маршрут с именем 'registration' существует
};
</script>

<style scoped>
/* Стили остаются прежними */
.login-container {
	height: calc(100vh - (54px + 5px));
	
	width: 100%;
	flex: 0 0 100%;
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: center;
	flex-wrap: nowrap;
	overflow-x: hidden;
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
	transition: background 0.3s ease;
}

button:hover {
	background: var(--primary-color-hover);
}

.error {
	color: red;
	margin-top: 10px;
}

span {
	display: block;
	text-align: center;
	margin-top: 15px;
}

a {
	color: var(--primary-color);
	text-decoration: none;
}
</style>