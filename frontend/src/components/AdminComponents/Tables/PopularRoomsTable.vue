<template>
	<div class="rooms-table">
		<h3>Популярные комнаты</h3>
		<div v-if="rooms.length === 0" class="empty-message">
			Нет данных о комнатах
		</div>
		<table v-else>
			<thead>
				<tr>
					<th>Название</th>
					<th>Участников</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="room in rooms" :key="room.id">
					<td>{{ room.name }}</td>
					<td>{{ room.members }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
defineProps({
	rooms: {
		type: Array,
		default: () => []
	}
});
</script>

<style scoped>
.rooms-table {
	background: var(--sidebar-bg-light);
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