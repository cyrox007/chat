<template>
	<div class="form-group">
		<label v-if="label" :for="id">{{ label }}</label>
		<div class="drop-zone" :class="{ 'drag-over': isDragging }" @dragover.prevent @dragenter="handleDragEnter"
			@dragleave="handleDragLeave" @drop="handleDrop">
			<label :for="id" class="custom-file-upload">
				<span>{{ placeholder }}</span>
			</label>
			<input :id="id" type="file" accept="image/*" @change="handleFileChange" style="display: none;" />
			<p>или перетащите файл сюда</p>
		</div>
		<img v-if="preview" :src="preview" alt="Preview" class="avatar-preview" />
		<p v-if="error" class="error">{{ error }}</p>
	</div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from "vue";

const props = defineProps({
	id: { type: String, required: true },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "Выбрать файл" },
	modelValue: { type: [Blob, null], default: null },
	maxSize: { type: Number, default: 10 * 1024 * 1024 }, // Максимальный размер файла (по умолчанию 10 МБ)
	error: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "validation-error"]);

const isDragging = ref(false);
const preview = ref(null);

// Проверка размера файла
const validateFileSize = (file) => {
	if (file.size > props.maxSize) {
		return `Файл слишком большой. Максимальный размер: ${props.maxSize / (1024 * 1024)} МБ.`;
	}
	return "";
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
					(blob) => {
						if (blob) {
							const webpFile = new File([blob], file.name || 'avatar.webp', { type: 'image/webp' });
							resolve(webpFile);
						} else {
							reject(new Error('Ошибка создания Blob'));
						}
					},
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

// Обработка файла
const handleFile = async (file) => {
	const sizeError = validateFileSize(file);
	if (sizeError) {
		emit("update:modelValue", null);
		return sizeError;
	}

	try {
		const webpBlob = await convertImageToWebP(file);
		preview.value = URL.createObjectURL(webpBlob);
		emit("update:modelValue", webpBlob);
		return "";
	} catch (error) {
		console.error("Ошибка конвертации в WebP:", error);
		return "Ошибка обработки изображения.";
	}
};

// Обработка события изменения файла
const handleFileChange = async (event) => {
	const file = event.target.files[0];
	if (file) {
		const errorMessage = await handleFile(file);
		emit("validation-error", errorMessage);
	}
};

// Обработка drag-and-drop
const handleDrop = async (event) => {
	event.preventDefault();
	isDragging.value = false;

	const file = event.dataTransfer.files[0];
	if (file) {
		const errorMessage = await handleFile(file);
		emit("validation-error", errorMessage);
	}
};

// Обработка событий drag-and-drop
const handleDragEnter = () => {
	isDragging.value = true;
};

const handleDragLeave = () => {
	isDragging.value = false;
};
</script>

<style scoped>
.drop-zone {
	position: relative;
	width: 100%;
	padding: 20px;
	border: 2px dashed #ccc;
	border-radius: 8px;
	text-align: center;
	cursor: pointer;
	transition: border-color 0.3s ease;
}

.drop-zone:hover {
	border-color: #007bff;
}

.drop-zone.drag-over {
	border-color: #007bff;
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

.avatar-preview {
	width: 100px;
	height: 100px;
	object-fit: cover;
	border-radius: 50%;
	margin-top: 10px;
	display: block;
}

.error {
	color: red;
	font-size: 12px;
}
</style>