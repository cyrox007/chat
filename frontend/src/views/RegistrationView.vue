<template>
	<div class="registration-container">
		<div class="registration-form">
			<h1>Регистрация</h1>

			<!-- Шаг 1: Основные данные -->
			<form v-if="step === 1" @submit.prevent="validateStep1">
				<div class="form-group">
					<label for="username">Имя пользователя:</label>
					<input type="text" id="username" v-model="formData.username" required
						placeholder="Введите имя пользователя" />
				</div>
				<div class="form-group">
					<label for="email">Email:</label>
					<input type="email" id="email" v-model="formData.email" required placeholder="Введите email" />
				</div>
				<div class="form-group">
					<label for="password">Пароль:</label>
					<input type="password" id="password" v-model="formData.password" required
						placeholder="Введите пароль" autocomplete="off" @copy.prevent @paste.prevent />
				</div>
				<div class="form-group">
					<label for="confirmPassword">Подтвердите пароль:</label>
					<input type="password" id="confirmPassword" v-model="formData.confirmPassword" required
						placeholder="Подтвердите пароль" autocomplete="off" @copy.prevent @paste.prevent />
				</div>
				<button type="submit" class="btn-primary">Продолжить</button>
				<p v-if="errorMessage" class="error">{{ errorMessage }}</p>
			</form>

			<!-- Шаг 2: Дополнительные данные -->
			<form v-if="step === 2" @submit.prevent="handleRegistration">
				<div class="form-group">
					<label for="first_name">Имя:</label>
					<input type="text" id="first_name" v-model="formData.first_name" placeholder="Введите имя" />
				</div>
				<div class="form-group">
					<label for="last_name">Фамилия:</label>
					<input type="text" id="last_name" v-model="formData.last_name" placeholder="Введите фамилию" />
				</div>
				<div class="form-group">
					<label for="date_of_birth">Дата рождения:</label>
					<input type="date" id="date_of_birth" v-model="formData.date_of_birth" />
				</div>
				<div class="form-group">
					<label for="gender">Пол:</label>
					<select id="gender" v-model="formData.gender">
						<option value="">Не указано</option>
						<option value="male">Мужской</option>
						<option value="female">Женский</option>
						<option value="other">Другой</option>
					</select>
				</div>
				<div class="form-group">
					<label for="bio">Биография:</label>
					<textarea id="bio" v-model="formData.bio" placeholder="Расскажите о себе"></textarea>
				</div>
				<button type="submit" class="btn-primary">Завершить регистрацию</button>
				<button type="button" class="btn-secondary" @click="goBackToStep1">Назад</button>
				<p v-if="errorMessage" class="error">{{ errorMessage }}</p>
			</form>

			<!-- Ссылка на страницу авторизации -->
			<span>
				Уже зарегистрированы?
				<router-link :to="{ name: 'login' }">Войти</router-link>
			</span>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

// Инициализация роутера
const router = useRouter();

// Состояния формы
const formData = ref({
	username: '',
	email: '',
	password: '',
	confirmPassword: '',
	first_name: '',
	last_name: '',
	date_of_birth: '',
	gender: '',
	bio: '',
});
const step = ref(1); // Текущий шаг
const errorMessage = ref('');

// Валидация первого шага
const validateStep1 = () => {
	if (formData.value.password !== formData.value.confirmPassword) {
		errorMessage.value = 'Пароли не совпадают.';
		return;
	}
	step.value = 2; // Переход ко второму шагу
};

// Обработчик регистрации
const handleRegistration = async () => {
	try {
		// Логика отправки данных на сервер
		const formDataToSend = new FormData();
		Object.keys(formData.value).forEach((key) => {
			formDataToSend.append(key, formData.value[key]);
		});

		console.log('Отправка данных:', formDataToSend);

		// Пример: await AuthService.register(formDataToSend);

		// Перенаправление на страницу авторизации
		router.push({ name: 'login' });
	} catch (error) {
		errorMessage.value = 'Ошибка регистрации. Попробуйте снова.';
		console.error('Ошибка при регистрации:', error);
	}
};

// Вернуться к первому шагу
const goBackToStep1 = () => {
	step.value = 1;
};
</script>

<style scoped>
.registration-container {
	display: flex;
	justify-content: center;
	align-items: center;
	height: calc(100vh - 5px);
	background-size: cover;
	background-position: center;
	margin: 0 auto;
}

.registration-form {
	width: 400px;
	padding: 20px;
	background: white;
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	border-radius: 8px;
}

h1 {
	text-align: center;
	margin-bottom: 20px;
}

.form-group {
	margin-bottom: 15px;
}

label {
	display: block;
	font-weight: bold;
	margin-bottom: 5px;
}

input[type='text'],
input[type='email'],
input[type='password'] {
	width: 100%;
	padding: 8px;
	border: 1px solid #ccc;
	border-radius: 4px;
}

textarea {
	width: 100%;
	padding: 8px;
	border: 1px solid #ccc;
	border-radius: 4px;
	resize: vertical;
}

button {
	width: 100%;
	padding: 10px;
	margin-top: 10px;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
}

.btn-primary {
	background: var(--primary-color);
	color: white;
}

.btn-primary:hover {
	background: var(--primary-color-hover);
}

.btn-secondary {
	background: #ccc;
	color: black;
}

.btn-secondary:hover {
	background: #bbb;
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

a:hover {
	text-decoration: underline;
}
</style>