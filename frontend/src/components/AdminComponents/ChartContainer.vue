<template>
	<div class="chart-container">
		<h3>{{ title }}</h3>
		<div class="chart-wrapper">
			<slot></slot>
		</div>
	</div>
</template>

<script setup>
defineProps({
	title: {
		type: String,
		required: true
	}
});
</script>

<style scoped>
.chart-container {
	background: white;
	border-radius: 8px;
	padding: 20px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-wrapper {
	margin-top: 20px;
	height: 300px;
}
</style>