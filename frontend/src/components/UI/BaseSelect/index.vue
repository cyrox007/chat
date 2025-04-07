<template>
	<div class="form-group">
		<label :for="id">{{ label }}</label>
		<select :id="id" v-model="localValue" :class="['form-control', { 'is-invalid': error }]"
			:placeholder="placeholder">
			<option value="" disabled>{{ placeholder }}</option>
			<option v-for="(option, index) in options" :key="index" :value="option.value">
				{{ option.label }}
			</option>
		</select>
		<div v-if="error" class="invalid-feedback">{{ error }}</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

// Пропсы компонента
const props = defineProps({
	id: {
		type: String,
		required: true,
	},
	label: {
		type: String,
		required: true,
	},
	placeholder: {
		type: String,
		default: "Выберите значение",
	},
	options: {
		type: Array,
		required: true,
	},
	modelValue: {
		type: [String, Number],
		default: "",
	},
	error: {
		type: String,
		default: "",
	},
});

// Эмиты компонента
const emit = defineEmits(["update:modelValue"]);

// Локальное значение для двусторонней привязки
const localValue = computed({
	get() {
		return props.modelValue;
	},
	set(value) {
		emit("update:modelValue", value);
	},
});
</script>

<style scoped>
.form-group {
	margin-bottom: 1rem;
}

label {
	display: block;
	margin-bottom: 0.5rem;
	font-weight: bold;
}

.form-control {
	width: 100%;
	padding: 0.5rem;
	border: 1px solid #ccc;
	border-radius: 4px;
	font-size: 1rem;
}

.form-control.is-invalid {
	border-color: #dc3545;
}

.invalid-feedback {
	color: #dc3545;
	font-size: 0.875rem;
}
</style>