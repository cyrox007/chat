<template>
	<div class="registration-container">
		<div class="registration-form">
			<h1>Регистрация</h1>

			<!-- Шаг 1: Основные данные -->
			<form v-if="step === 1" @submit.prevent="validateStep1">
				<BaseInput id="username" label="Имя пользователя" placeholder="Введите имя пользователя"
					v-model="formData.username" :error="usernameError"
					:validationRules="(value) => !value ? 'Поле обязательно' : ''"
					:asyncValidation="checkUsernameUniqueness" />

				<BaseInput id="email" label="Email" type="email" placeholder="Введите email" v-model="formData.email"
					:error="emailError" :validationRules="(value) => !value ? 'Поле обязательно' : ''"
					:asyncValidation="checkEmailUniqueness" />
				
				<BaseInput id="phone" label="Телефон" type="phone" placeholder="Введите номер телефона" v-model="formData.phone"
					:error="phoneError" :validationRules="(value) => !value ? 'Поле обязательно' : ''"
					:asyncValidation="checkPhoneUniqueness" />

				<BaseInput id="password" label="Пароль" type="password" placeholder="Введите пароль"
					v-model="formData.password" :error="passwordError" />

				<BaseInput id="confirmPassword" label="Подтвердите пароль" type="password"
					placeholder="Подтвердите пароль" v-model="formData.confirmPassword" :error="confirmPasswordError" />

				<button type="submit" class="btn-primary">Продолжить</button>
			</form>

			<!-- Шаг 2 -->
			<form v-if="step === 2" @submit.prevent="handleRegistration">
				<BaseInput id="first_name" label="Имя" placeholder="Введите имя" v-model="formData.first_name" />

				<BaseInput id="last_name" label="Фамилия" placeholder="Введите фамилию" v-model="formData.last_name" />

				<BaseSelect
					id="gender"
					label="Пол"
					placeholder="Выберите пол"
					v-model="formData.gender"
					:options="[
						{ value: 'male', label: 'Мужской' },
						{ value: 'female', label: 'Женский' }
					]"
				/>

				<BaseInput id="date_of_birth" label="Дата рождения" type="date" v-model="formData.date_of_birth" />

				<BaseTextarea id="bio" label="Биография" placeholder="Расскажите о себе" v-model="formData.bio" />

				<BaseFileUpload id="avatar" label="Аватар" placeholder="Выбрать файл" v-model="formData.avatar"
					:max-size="10 * 1024 * 1024" @validation-error="(message) => (avatarError = message)" />

				<button type="submit" class="btn-primary">Завершить регистрацию</button>
				<button type="button" class="btn-secondary" @click="goBackToStep1">Назад</button>
			</form>

			<!-- Ссылка на страницу авторизации -->
			<span class="link">
				Уже зарегистрированы?
				<router-link :to="{ name: 'login' }">Войти</router-link>
			</span>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

import AuthService from '@/API/AuthService';
import CSRFService from '@/API/CSRFService';

import BaseInput from "@/components/UI/BaseInput/index.vue";
import BaseTextarea from "@/components/UI/BaseTextarea/index.vue";
import BaseFileUpload from "@/components/UI/BaseFileUpload/index.vue";
import BaseSelect from "@/components/UI/BaseSelect/index.vue"

// Инициализация роутера
const router = useRouter();

// Состояния формы
const formData = ref({
	username: '',
	email: '',
	phone: '',
	password: '',
	confirmPassword: '',
	first_name: '',
	last_name: '',
	date_of_birth: '',
	gender: '',
	bio: '',
	avatar: null,
});
const step = ref(1); // Текущий шаг
const errorMessage = ref('');
const usernameError = ref('');
const emailError = ref('');
const phoneError = ref('');
const passwordError = ref('');
const confirmPasswordError = ref('');
const avatarError = ref('');

// Валидация первого шага
const validateStep1 = () => {
	if (!formData.value.username) {
		usernameError.value = 'Имя пользователя обязательно.';
		return;
	}
	if (!formData.value.email) {
		emailError.value = 'Email обязателен.';
		return;
	}
	if (formData.value.password.length < 8) {
		passwordError.value = 'Пароль должен содержать минимум 8 символов.';
		return;
	}
	if (formData.value.password !== formData.value.confirmPassword) {
		confirmPasswordError.value = 'Пароли не совпадают.';
		return;
	}
	step.value = 2; // Переход ко второму шагу
};

// Проверка уникальности имени пользователя
const checkUsernameUniqueness = async () => {
	if (!formData.value.username || formData.value.username === '') {
		usernameError.value = "Поле имени пользователя не может быть пустым";
	}

	try {
		const response = await AuthService.checkUsername(formData.value.username);
		if (!response.data.isUnique) {
			usernameError.value = 'Имя пользователя уже занято.';
		} else {
			usernameError.value = '';
		}
	} catch (error) {
		console.error('Ошибка проверки имени пользователя:', error);
	}
};

// Проверка уникальности email
const checkEmailUniqueness = async () => {
	// Проверяем, что поле email не пустое и содержит допустимое значение
	if (!formData.value.email || formData.value.email.trim() === '') {
		emailError.value = 'Поле email не может быть пустым.';
		return;
	}

	// Регулярное выражение для проверки допустимых символов (только латинские буквы, цифры и подчеркивание)
	const validUsernamePattern = /^[a-zA-Z0-9_]+$/;

	// Проверяем, соответствует ли имя пользователя допустимому формату
	if (!validUsernamePattern.test(formData.value.username)) {
		usernameError.value = "Имя пользователя может содержать только латинские буквы, цифры и символ подчеркивания.";
		return;
	}

	try {
		// Отправляем запрос на сервер для проверки уникальности email
		const response = await AuthService.checkEmail(formData.value.email);

		// Если email уже используется, устанавливаем сообщение об ошибке
		if (!response.data.isUnique) {
			emailError.value = 'Email уже используется.';
		} else {
			emailError.value = ''; // Очищаем ошибку, если email уникален
		}
	} catch (error) {
		// Логируем ошибку и устанавливаем сообщение для пользователя
		console.error('Ошибка проверки email:', error);

		// Если сервер вернул статус 400, выводим сообщение о некорректных данных
		if (error.response && error.response.status === 400) {
			emailError.value = 'Некорректный формат email.';
		} else {
			emailError.value = 'Произошла ошибка при проверке email. Попробуйте позже.';
		}
	}
};

const checkPhoneUniqueness = async () => {
	if (!formData.value.phone || formData.value.phone.trim() === '') {
		phoneError.value = 'Поле не может быть пустым.';
		return;
	}

	try {
		// Отправляем запрос на сервер для проверки уникальности email
		const response = await AuthService.checkPhone(formData.value.email);

		// Если email уже используется, устанавливаем сообщение об ошибке
		if (!response.data.isUnique) {
			phoneError.value = 'Номер телефона уже используется.';
		} else {
			phoneError.value = ''; // Очищаем ошибку, если email уникален
		}
	} catch (error) {
		// Логируем ошибку и устанавливаем сообщение для пользователя
		console.error('Ошибка проверки поля:', error);

		// Если сервер вернул статус 400, выводим сообщение о некорректных данных
		if (error.response && error.response.status === 400) {
			phoneError.value = 'Некорректный формат номера.';
		} else {
			phoneError.value = 'Произошла ошибка при проверке номера телефона. Попробуйте позже.';
		}
	}
}

// Обработчик загрузки аватара
/* const handleAvatarUpload = (event) => {
	const file = event.target.files[0];
	if (file) {
		if (file.size > 10 * 1024 * 1024) {
			avatarError.value = 'Файл слишком большой. Максимальный размер: 10 МБ.';
			return;
		}
		convertImageToWebP(file).then((webpBlob) => {
			formData.value.avatar = webpBlob;
			previewAvatar.value = URL.createObjectURL(webpBlob);
			avatarError.value = '';
		}).catch((error) => {
			avatarError.value = 'Ошибка обработки изображения.';
			console.error('Ошибка конвертации в WebP:', error);
		});
	}
};

// Конвертация изображения в WebP
const convertImageToWebP = (file) => {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = (e) => {
			const img = new Image();
			img.src = e.target.result;
			img.onload = () => {
				const canvas = document.createElement('canvas');
				const ctx = canvas.getContext('2d');
				canvas.width = img.width;
				canvas.height = img.height;
				ctx.drawImage(img, 0, 0);
				canvas.toBlob(
					(blob) => blob ? resolve(blob) : reject(new Error('Ошибка создания Blob')),
					'image/webp',
					0.75 // Качество сжатия
				);
			};
			img.onerror = reject;
		};
		reader.onerror = reject;
		reader.readAsDataURL(file);
	});
}; */

// Обработчик регистрации
const handleRegistration = async () => {
	try {
		// Создаем FormData для отправки
		const formDataToSend = new FormData();
		Object.keys(formData.value).forEach((key) => {
			if (key === 'avatar' && formData.value[key]) {
				formDataToSend.append(key, formData.value[key], 'avatar.webp');
			} else {
				formDataToSend.append(key, formData.value[key]);
			}
		});

		// Вызываем метод регистрации через AuthService
		await AuthService.registration(formDataToSend);

		// Перенаправляем пользователя на страницу авторизации
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

// Запрос CSRF-токена при загрузке страницы
onMounted(async () => {
	try {
		await CSRFService.getCSRF(); 
	} catch (error) {
		console.error('Failed to fetch CSRF token:', error);
	}
});
</script>

<style scoped>
.registration-container {
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

.registration-form {
	width: 400px;
	padding: 20px;
	background: var(--bg-light);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	border-radius: 8px;
}

h1 {
	text-align: center;
	margin-bottom: 20px;
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
span.link {
	display: block;
	text-align: center;
	margin-top: 15px;
}
span.link a {
	color: var(--primary-color);
  	text-decoration: none;
}
</style>