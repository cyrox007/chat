<template>
	<div class="not-found">
		<h1>404</h1>
		<p>Страница не найдена.</p>
		<router-link to="/">Вернуться на главную</router-link>
	</div>
</template>

<script setup>
</script>

<style scoped>
.not-found {
	text-align: center;
	margin-top: 50px;
}

h1 {
	font-size: 48px;
	color: #ff4d4d;
}

p {
	font-size: 24px;
	margin-bottom: 20px;
}

a {
	text-decoration: none;
	color: #007bff;
	font-weight: bold;
}

a:hover {
	text-decoration: underline;
}
</style>