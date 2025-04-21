<template>
	<div class="avatar-upload-modal" :class="isModalOpen ? 'active' : ''">
		<!-- Фон для затемнения -->
		<div class="modal-overlay" @click="closeModal"></div>

		<!-- Основное окно модалки -->
		<div class="modal-content">
			<h2>Обновление аватара</h2>

			<!-- Предварительный просмотр аватара -->
			<div class="preview-container">
				<img v-if="previewImage" :src="previewImage" alt="Предпросмотр аватара" class="preview-image" />
				<p v-else>Выберите файл для предпросмотра</p>
			</div>

			<!-- Выбор файла -->
			<div class="file-input-container">
				<label for="avatar-upload" class="upload-button">
					Выбрать файл
				</label>
				<input id="avatar-upload" type="file" accept="image/*" @change="handleFileSelect"
					style="display: none" />
			</div>

			<!-- Кнопки действий -->
			<div class="action-buttons">
				<button class="btn-cancel" @click="closeModal">Отмена</button>
				<button class="btn-upload" @click="uploadAvatar" :disabled="!selectedFile">
					Загрузить
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue';
import { processFile } from '@/utils/fileUtils';
import UsersServices from '@/API/UsersService';

// Пропсы
const props = defineProps({
	isModalOpen: {
		type: Boolean,
		default: false,
	},
	user_uid: {
		type: String,
		require: true
	}
});

// Эмит события закрытия модального окна
const emit = defineEmits(['close', 'upload']);

// Состояния
const selectedFile = ref(null); // Выбранный файл
const previewImage = ref(null); // URL предпросмотра

// Обработка выбора файла
const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
        // Обрабатываем файл с опциями сжатия
        const { base64, meta } = await processFile(file, {
            maxWidth: 800, // Максимальная ширина
            quality: 0.8, // Качество изображения
        });

        // Сохраняем выбранный файл в нужном формате
        selectedFile.value = {
            url: `data:${meta.type};base64,${base64}`, // Base64-строка с MIME-типом
            type: meta.type, // MIME-тип файла
            name: meta.name, // Имя файла
            size: meta.size, // Размер файла в байтах
        };

        // Предпросмотр изображения
        previewImage.value = selectedFile.value.url;
    } catch (error) {
        console.error('Ошибка при обработке файла:', error);
        alert('Не удалось обработать файл.');
    }
};

// Закрытие модального окна
const closeModal = () => {
	selectedFile.value = null;
	previewImage.value = null;
	emit('close');
};

// Загрузка аватара на сервер
const uploadAvatar = async () => {
    if (!selectedFile.value) return;

    try {
        // Отправляем JSON-объект с данными файла
        const response = await UsersServices.updateProfile(props.user_uid, {avatar: selectedFile.value});

        if (response.data.status === 'ok') {
            emit('upload', response.data); // Эмитируем событие успешной загрузки
            closeModal(); // Закрываем модальное окно
        } else {
            console.error('Ошибка при загрузке аватара:', response.data.message);
            alert('Не удалось загрузить аватар.');
        }
    } catch (error) {
        console.error('Ошибка при загрузке аватара:', error);
        alert('Произошла ошибка при загрузке аватара.');
    }
};
</script>

<style scoped>
.avatar-upload-modal {
	position: fixed;
	top: 0;
	bottom: 0;
	left: 0;
	right: 0;
	width: 100%;
	height: 100%;
	background: rgba(0, 0, 0, 0.5);
	z-index: -9999;
	display: flex;
	justify-content: center;
	align-items: center;
	opacity: 0;
}

.avatar-upload-modal {
	opacity: 1;
	z-index: 9999;
}

.modal-overlay {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	z-index: 1;
}

.modal-content {
	background: white;
	padding: 20px;
	border-radius: 8px;
	width: 100%;
	max-width: 500px;
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
	z-index: 2;
}

.modal-content h2 {
	margin-bottom: 20px;
	font-size: 1.5em;
	text-align: center;
}

.preview-container {
	display: flex;
	justify-content: center;
	align-items: center;
	margin-bottom: 20px;
	height: 150px;
}

.preview-image {
	max-width: 100%;
	max-height: 100%;
	border-radius: 8px;
}

.file-input-container {
	margin-bottom: 20px;
	text-align: center;
}

.upload-button {
	display: inline-block;
	padding: 10px 20px;
	background: var(--primary-color);
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
}

.upload-button:hover {
	background: var(--primary-color-hover);
}

.action-buttons {
	display: flex;
	justify-content: space-between;
}

.action-buttons button {
	padding: 10px 20px;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
}

.btn-cancel {
	background: #ccc;
	color: black;
}

.btn-cancel:hover {
	background: #bbb;
}

.btn-upload {
	background: var(--primary-color);
	color: white;
}

.btn-upload:hover {
	background: var(--primary-color-hover);
}
</style>