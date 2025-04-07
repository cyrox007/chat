<template>
	<div class="form-group">
		<label v-if="label" :for="id">{{ label }}</label>
		<input :id="id" :type="type" :value="modelValue" :placeholder="placeholder"
			@input="$emit('update:modelValue', $event.target.value)" :class="{ 'has-error': error }" />
		<p v-if="error" class="error">{{ error }}</p>
	</div>
</template>

<script setup>
defineProps({
	id: { type: String, required: true },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	modelValue: { type: [String, Number], default: "" },
	type: { type: String, default: "text" },
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