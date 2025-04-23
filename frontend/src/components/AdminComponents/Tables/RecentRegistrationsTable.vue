<template>
	<div class="registrations-table">
		<h3>Последние регистрации</h3>
		<div v-if="users.length === 0" class="empty-message">
			Нет данных о пользователях
		</div>
		<table v-else>
			<thead>
				<tr>
					<th>Имя пользователя</th>
					<th>Дата регистрации</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="user in users" :key="user.id">
					<td>{{ user.username }}</td>
					<td>{{ formatDate(user.created_at) }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
	users: {
		type: Array,
		default: () => []
	}
});

const formatDate = (dateString) => {
	return new Date(dateString).toLocaleString();
};
</script>

<style scoped>
.registrations-table {
	background: white;
	border-radius: 8px;
	padding: 20px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

table {
	width: 100%;
	border-collapse: collapse;
}

th,
td {
	padding: 12px 15px;
	text-align: left;
	border-bottom: 1px solid #eee;
}

.empty-message {
	padding: 20px;
	text-align: center;
	color: #666;
}
</style>