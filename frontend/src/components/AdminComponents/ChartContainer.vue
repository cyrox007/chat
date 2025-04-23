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
	background: var(--sidebar-bg-light);
	border-radius: 8px;
	padding: 20px;
	box-shadow: var(--shadow-light);
	color: var(--text-light);
}

.chart-container h3 {
	margin: 0 0 16px 0;
	font-size: 16px;
	font-weight: 500;
	color: var(--text-light);
}

.chart-wrapper {
	margin-top: 20px;
	height: 300px;
	position: relative;
}
</style>