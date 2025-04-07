<template>
	<div class="form-group">
		<label v-if="label" :for="id">{{ label }}</label>
		<textarea :id="id" :value="modelValue" :placeholder="placeholder"
			@input="$emit('update:modelValue', $event.target.value)" :class="{ 'has-error': error }"></textarea>
		<p v-if="error" class="error">{{ error }}</p>
	</div>
</template>

<script setup>
defineProps({
	id: { type: String, required: true },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	modelValue: { type: String, default: "" },
	error: { type: String, default: "" },
});

defineEmits(["update:modelValue"]);
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

textarea {
	width: 100%;
	padding: 8px;
	border: 1px solid #ccc;
	border-radius: 4px;
	resize: vertical;
}

textarea.has-error {
	border-color: red;
}

.error {
	color: red;
	font-size: 12px;
}
</style>