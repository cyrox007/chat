<template>
	<div class="registration-container">
		<div class="registration-form">
			<h1>Регистрация</h1>

			<!-- Шаг 1: Основные данные -->
			<form v-if="step === 1" @submit.prevent="validateStep1">
				<div class="form-group">
					<label for="username">Имя пользователя:</label>
					<input type="text" id="username" v-model="formData.username" required
						placeholder="Введите имя пользователя" @blur="checkUsernameUniqueness" />
					<p v-if="usernameError" class="error">{{ usernameError }}</p>
				</div>
				<div class="form-group">
					<label for="email">Email:</label>
					<input type="email" id="email" v-model="formData.email" required placeholder="Введите email"
						@blur="checkEmailUniqueness" />
					<p v-if="emailError" class="error">{{ emailError }}</p>
				</div>
				<div class="form-group">
					<label for="gender">Пол:</label>
					<select id="gender" v-model="formData.gender">
						<option value="">Не указано</option>
						<option value="male">Мужской</option>
						<option value="female">Женский</option>
					</select>
				</div>
				<div class="form-group">
					<label for="password">Пароль:</label>
					<input type="password" id="password" v-model="formData.password" required
						placeholder="Введите пароль" autocomplete="off" @copy.prevent @paste.prevent />
					<p v-if="passwordError" class="error">{{ passwordError }}</p>
				</div>
				<div class="form-group">
					<label for="confirmPassword">Подтвердите пароль:</label>
					<input type="password" id="confirmPassword" v-model="formData.confirmPassword" required
						placeholder="Подтвердите пароль" autocomplete="off" @copy.prevent @paste.prevent />
					<p v-if="confirmPasswordError" class="error">{{ confirmPasswordError }}</p>
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
					<label for="bio">Биография:</label>
					<textarea id="bio" v-model="formData.bio" placeholder="Расскажите о себе"></textarea>
				</div>
				<div class="form-group">
					<label for="avatar">Аватар:</label>
					<div class="avatar-upload">
						<label for="avatar-input" class="custom-file-upload">
							<span>Выбрать файл</span>
						</label>
						<input type="file" id="avatar-input" accept="image/*" @change="handleAvatarUpload"
							style="display: none;" />
					</div>
					<p v-if="avatarError" class="error">{{ avatarError }}</p>
					<img v-if="previewAvatar" :src="previewAvatar" alt="Preview Avatar" class="avatar-preview" />
				</div>
				<button type="submit" class="btn-primary">Завершить регистрацию</button>
				<button type="button" class="btn-secondary" @click="goBackToStep1">Назад</button>
				<p v-if="errorMessage" class="error">{{ errorMessage }}</p>
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
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import AuthService from '@/API/AuthService';

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
	avatar: null,
});
const step = ref(1); // Текущий шаг
const errorMessage = ref('');
const usernameError = ref('');
const emailError = ref('');
const passwordError = ref('');
const confirmPasswordError = ref('');
const avatarError = ref('');
const previewAvatar = ref(null);

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

// Обработчик загрузки аватара
const handleAvatarUpload = (event) => {
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
};

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

span.link {
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

.avatar-preview {
	width: 100px;
	height: 100px;
	object-fit: cover;
	border-radius: 50%;
	margin-top: 10px;
	display: block;
}

.avatar-upload {
	position: relative;
}

.custom-file-upload {
	display: inline-block;
	padding: 8px 16px;
	background-color: #007bff;
	color: white;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
	text-align: center;
}

.custom-file-upload:hover {
	background-color: #0056b3;
}

#avatar-input {
	display: none;
}
</style>