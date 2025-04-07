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
import { ref } from "vue";

const props = defineProps({
	id: { type: String, required: true },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "Выбрать файл" },
	modelValue: { type: [File, null], default: null },
	error: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const isDragging = ref(false);
const preview = ref(null);

const handleDragEnter = () => {
	isDragging.value = true;
};

const handleDragLeave = () => {
	isDragging.value = false;
};

const handleDrop = (event) => {
	event.preventDefault();
	isDragging.value = false;

	const file = event.dataTransfer.files[0];
	handleFile(file);
};

const handleFileChange = (event) => {
	const file = event.target.files[0];
	handleFile(file);
};

const handleFile = (file) => {
	if (file) {
		if (file.size > 10 * 1024 * 1024) {
			return;
		}
		preview.value = URL.createObjectURL(file);
		emit("update:modelValue", file);
	}
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