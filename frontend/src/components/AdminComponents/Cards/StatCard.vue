<template>
	<div class="stat-card" :class="`bg-${color}`">
		<div class="stat-icon">
			<i :class="`fas fa-${icon}`"></i>
		</div>
		<div class="stat-content">
			<h3>{{ title }}</h3>
			<p class="stat-value">{{ value }}</p>
		</div>
	</div>
</template>

<script setup>
defineProps({
	title: String,
	value: [Number, String],
	icon: String,
	color: {
		type: String,
		default: 'blue'
	}
});
</script>

<style scoped>
.stat-card {
	display: flex;
	align-items: center;
	padding: 20px;
	border-radius: 8px;
	color: white;
	box-shadow: var(--shadow-light);
}

.stat-icon {
	font-size: 2rem;
	margin-right: 15px;
}

.stat-content h3 {
	margin: 0 0 5px 0;
	font-size: 1rem;
}

.stat-value {
	margin: 0;
	font-size: 1.8rem;
	font-weight: bold;
}

.bg-blue {
	background-color: #4299E1;
}

.bg-green {
	background-color: #48BB78;
}

.bg-purple {
	background-color: #9F7AEA;
}

.bg-orange {
	background-color: #ED8936;
}
</style>