<template>
	<div class="create-room-modal" :class="{ active: isShow }">
		<!-- Фон для затемнения -->
		<div class="modal-overlay" @click="closeModal"></div>

		<!-- Основная форма -->
		<div class="create-room-form">
			<h2>Создание новой комнаты</h2>

			<!-- Поле названия комнаты -->
			<div class="form-group">
				<label for="name">Название комнаты:</label>
				<input type="text" id="name" v-model="formData.name" placeholder="Введите название комнаты" required />
			</div>

			<!-- Поле описания -->
			<div class="form-group">
				<label for="description">Описание:</label>
				<textarea id="description" v-model="formData.description"
					placeholder="Введите описание комнаты"></textarea>
			</div>

			<!-- Поле региона -->
			<div class="form-group">
				<label for="region">Регион:</label>
				<input type="text" id="region" v-model="formData.region" placeholder="Введите регион" required />
			</div>

			<!-- Поле страны -->
			<div class="form-group">
				<label for="country">Страна:</label>
				<input type="text" id="country" v-model="formData.country" placeholder="Введите страну" required />
			</div>

			<!-- Поле тегов -->
			<div class="form-group">
				<label for="tags">Теги (через запятую):</label>
				<input type="text" id="tags" v-model="formData.tags" placeholder="Введите теги" />
			</div>

			<!-- Кнопки действий -->
			<div class="form-actions">
				<button class="btn-cancel" @click="closeModal">Отмена</button>
				<button class="btn-create" @click="createRoom">
					<span v-if="!isLoading">Создать</span>
					<span v-else>Загрузка...</span>
				</button>
			</div>

			<!-- Спиннер -->
			<div v-if="isLoading" class="spinner-overlay">
				<div class="spinner"></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue';
import RoomService from '@/API/RoomsService'; // Предполагается, что у вас есть сервис для работы с комнатами
import CSRFService from '@/API/CSRFService';

// Пропсы
const props = defineProps({
	isShow: {
		type: Boolean,
		default: false,
	},
});

// Эмит события закрытия модального окна
const emit = defineEmits(['close']);

// Модель данных формы
const formData = ref({
	name: '',
	description: '',
	region: '',
	country: '',
	tags: '',
});

const isLoading = ref(false);

// Правила валидации
const validationRules = {
	name: {
		required: true,
		pattern: /^[a-zA-Z0-9а-яА-ЯёЁ\s\-_]{3,50}$/, // Разрешены буквы, цифры, пробелы, дефисы и подчеркивания
		message: 'Название комнаты должно быть от 3 до 50 символов и содержать только буквы, цифры, пробелы, дефисы или подчеркивания.',
	},
	description: {
		required: false,
		pattern: /^[a-zA-Z0-9а-яА-ЯёЁ\s\-\.,!?_]{0,200}$/, // Опционально, максимум 200 символов
		message: 'Описание должно быть не длиннее 200 символов и не содержать специальных символов.',
	},
	region: {
		required: false,
		pattern: /^[a-zA-Zа-яА-ЯёЁ\s\-]{0,50}$/, // Опционально, максимум 50 символов
		message: 'Регион должен содержать только буквы, пробелы и дефисы.',
	},
	country: {
		required: false,
		pattern: /^[a-zA-Zа-яА-ЯёЁ\s\-]{0,50}$/, // Опционально, максимум 50 символов
		message: 'Страна должна содержать только буквы, пробелы и дефисы.',
	},
	tags: {
		required: false,
		pattern: /^[a-zA-Z0-9а-яА-ЯёЁ\s\-,]{0,100}$/, // Опционально, максимум 100 символов
		message: 'Теги должны содержать только буквы, цифры, пробелы, запятые и дефисы.',
	},
};

const validateForm = () => {
	const errors = {};

	for (const [key, rule] of Object.entries(validationRules)) {
		const value = formData.value[key];

		// Проверка обязательных полей
		if (rule.required && (!value || value.trim() === '')) {
			errors[key] = `${rule.message || 'Это поле обязательно.'}`;
			continue;
		}

		// Проверка формата
		if (rule.pattern && value && !rule.pattern.test(value)) {
			errors[key] = rule.message || 'Неверный формат данных.';
		}
	}

	return errors;
};

// Закрытие модального окна
const closeModal = () => {
	emit('close');
};

// Создание комнаты
const createRoom = async () => {
	const errors = validateForm();

	if (Object.keys(errors).length > 0) {
		console.error('Ошибки валидации:', errors);
		alert('Пожалуйста, исправьте ошибки в форме.');
		return;
	}

	try {
		// Подготовка данных для отправки
		const roomData = {
			name: formData.value.name,
			description: formData.value.description,
			region: formData.value.region,
			country: formData.value.country,
			tags: formData.value.tags.split(',').map((tag) => tag.trim()), // Разделяем теги по запятой
		};
		await CSRFService.getCSRF();
		// Отправка данных на сервер
		const response = await RoomService.create_room(roomData);

		if (response.data.status === 'ok') {
			console.log('Комната успешно создана:', response.data.room);
			closeModal(); // Закрываем модальное окно
			resetForm(); // Очищаем форму
			emit('create-room-complete')
		} else {
			console.error('Ошибка при создании комнаты:', response.data.message);
		}
	} catch (error) {
		console.error('Ошибка при создании комнаты:', error);
	}
};

// Сброс формы
const resetForm = () => {
	formData.value = {
		name: '',
		description: '',
		region: '',
		country: '',
		tags: '',
	};
};
</script>

<style scoped>
/* Основной контейнер модального окна */
.create-room-modal {
	position: fixed;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	background: rgba(0, 0, 0, 0.5);
	z-index: -9999;
	opacity: 0;
	display: flex;
	justify-content: center;
	align-items: center;
	transition: opacity 0.3s ease;
}

.create-room-modal.active {
	opacity: 1;
	z-index: 9999;
}

/* Фон для затемнения */
.modal-overlay {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
}

/* Форма */
.create-room-form {
	position: relative;
	background: white;
	padding: 20px;
	border-radius: 8px;
	width: 100%;
	max-width: 500px;
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

/* Заголовок */
.create-room-form h2 {
	margin-bottom: 20px;
	font-size: 1.5em;
	text-align: center;
}

/* Группа полей */
.form-group {
	margin-bottom: 15px;
}

.form-group label {
	display: block;
	margin-bottom: 5px;
	font-weight: bold;
}

.form-group input,
.form-group textarea {
	width: 100%;
	padding: 10px;
	border: 1px solid #ccc;
	border-radius: 4px;
	font-size: 1em;
}

.form-group textarea {
	resize: vertical;
	min-height: 80px;
}

/* Кнопки действий */
.form-actions {
	display: flex;
	justify-content: space-between;
	margin-top: 20px;
}

.form-actions button {
	padding: 10px 20px;
	border: none;
	border-radius: 4px;
	font-size: 1em;
	cursor: pointer;
	transition: background-color 0.3s ease;
}

.btn-cancel {
	background: #ccc;
	color: black;
}

.btn-cancel:hover {
	background: #bbb;
}

.btn-create {
	background: var(--primary-color);
	color: white;
}

.btn-create:hover {
	background: var(--primary-color-hover);
}
/* Стили для спиннера */
.spinner-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.8); /* Полупрозрачный фон */
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

.spinner {
    border: 4px solid #f3f3f3; /* Светлый цвет границы */
    border-top: 4px solid var(--primary-color); /* Цвет спиннера */
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% {
        transform: rotate(0deg);
    }
    100% {
        transform: rotate(360deg);
    }
}
</style>