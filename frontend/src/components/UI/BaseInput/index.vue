<template>
	<div class="form-group">
		<label v-if="label" :for="id">{{ label }}</label>
		<input :id="id" :type="type" :value="modelValue" :placeholder="placeholder"
			@input="$emit('update:modelValue', $event.target.value)" :class="{ 'has-error': error }"
			@blur="validateInput" />
		<p v-if="error" class="error">{{ error }}</p>
	</div>
</template>

<script setup>
import { defineEmits, defineProps } from 'vue';

const props = defineProps({
	id: { type: String, required: true },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	modelValue: { type: [String, Number], default: "" },
	type: { type: String, default: "text" },
	error: { type: String, default: "" },
	validationRules: { type: Function, default: null }, // Синхронная валидация
	asyncValidation: { type: Function, default: null }, // Асинхронная валидация
});

const emit = defineEmits(["update:modelValue", "validation-error"]);

const validateInput = async (event) => {
	const value = event.target.value;

	// Сначала выполняем синхронную валидацию
	if (props.validationRules) {
		const errorMessage = props.validationRules(value);
		emit("validation-error", errorMessage);
		if (errorMessage) return;
	}

	// Затем выполняем асинхронную валидацию
	if (props.asyncValidation) {
		try {
			const errorMessage = await props.asyncValidation(value);
			emit("validation-error", errorMessage);
		} catch (error) {
			console.error("Ошибка асинхронной валидации:", error);
		}
	}
};

</script>

<style scoped>
.form-group {
	margin-bottom: 15px;
}

label {
	display: block;
	font-weight: bold;
	margin-bottom: 5px;
}

input {
	width: 100%;
	padding: 8px;
	border: 1px solid #ccc;
	border-radius: 4px;
}

input.has-error {
	border-color: red;
}

.error {
	color: red;
	font-size: 12px;
}
</style>