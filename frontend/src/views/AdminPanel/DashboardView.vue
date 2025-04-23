<template>
	<div class="dashboard">
		<h1>Административная консоль</h1>

		<div class="stats-grid">
			<StatCard title="Всего пользователей" :value="stats.total_users" icon="users" color="blue" />
			<StatCard title="Онлайн сейчас" :value="stats.online_users" icon="user-check" color="green" />
			<StatCard title="Активных комнат" :value="stats.active_rooms" icon="comments" color="purple" />
			<StatCard title="Новых сегодня" :value="stats.new_today" icon="user-plus" color="orange" />
		</div>

		<div class="charts-grid">
			<ChartContainer title="Пользователи по полу">
				<GenderChart :data="stats.gender_data" />
			</ChartContainer>

			<ChartContainer title="География пользователей">
				<GeoChart :data="stats.geo_data" />
			</ChartContainer>

			<ChartContainer title="Устройства">
				<DevicesChart :data="stats.devices_data" />
			</ChartContainer>

			<ChartContainer title="Активность по времени">
				<ActivityChart :data="stats.activity_data" />
			</ChartContainer>
		</div>

		<div class="tables-section">
			<PopularRoomsTable :rooms="stats.popular_rooms" />
			<RecentRegistrationsTable :users="stats.recent_users" />
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import StatCard from '@/components/AdminComponents/Cards/StatCard.vue';
import ChartContainer from '@/components/AdminComponents/ChartContainer.vue';
import GenderChart from '@/components/AdminComponents/Charts/GenderChart.vue';
import GeoChart from '@/components/AdminComponents/Charts/GeoChart.vue';
import DevicesChart from '@/components/AdminComponents/Charts/DevicesChart.vue';
import ActivityChart from '@/components/AdminComponents/Charts/ActivityChart.vue';
import PopularRoomsTable from '@/components/AdminComponents/Tables/PopularRoomsTable.vue';
import RecentRegistrationsTable from '@/components/AdminComponents/Tables/RecentRegistrationsTable.vue';
import AdminService from '@/API/Admin/AdminService';

const stats = ref({
	total_users: 0,
	online_users: 0,
	active_rooms: 0,
	new_today: 0,
	gender_data: [],
	geo_data: [],
	devices_data: {
		by_model: [],
		by_type: [],
		active_now: 0
	},
	activity_data: [],
	popular_rooms: [],
	recent_users: []
});

onMounted(async () => {
	try {
		const response = await AdminService.getDashboardStats();
		stats.value = response.data.stats; // Обратите внимание на .stats
	} catch (error) {
		console.error('Ошибка загрузки статистики:', error);
	}
});
</script>

<style scoped>
.dashboard {
	padding: 20px;
}

.stats-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
	gap: 20px;
	margin-bottom: 30px;
}

.charts-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
	gap: 20px;
	margin-bottom: 30px;
}

.tables-section {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 20px;
}

@media (max-width: 1200px) {
	.tables-section {
		grid-template-columns: 1fr;
	}
}
</style>