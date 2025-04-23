<template>
	<div class="dashboard">
		<h1>Административная консоль</h1>

		<div class="stats-grid">
			<!-- Карточки с основной статистикой -->
			<StatCard title="Всего пользователей" :value="stats.totalUsers" icon="users" color="blue" />

			<StatCard title="Онлайн сейчас" :value="stats.onlineUsers" icon="user-check" color="green" />

			<StatCard title="Активных комнат" :value="stats.activeRooms" icon="comments" color="purple" />

			<StatCard title="Новых сегодня" :value="stats.newToday" icon="user-plus" color="orange" />
		</div>

		<div class="charts-grid">
			<!-- Диаграммы -->
			<ChartContainer title="Пользователи по полу">
				<GenderChart :data="stats.genderData" />
			</ChartContainer>

			<ChartContainer title="География пользователей">
				<GeoChart :data="stats.geoData" />
			</ChartContainer>

			<ChartContainer title="Устройства">
				<DevicesChart :data="stats.devicesData" />
			</ChartContainer>

			<ChartContainer title="Активность по времени">
				<ActivityChart :data="stats.activityData" />
			</ChartContainer>
		</div>

		<div class="tables-section">
			<PopularRoomsTable :rooms="stats.popularRooms" />
			<RecentRegistrationsTable :users="stats.recentUsers" />
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import StatCard from '@/components/AdminComponents/Cards/StatCard.vue';
//import ChartContainer from '@/components/Admin/ChartContainer.vue';
import GenderChart from '@/components/AdminComponents/Charts/GenderChart.vue';
//import GeoChart from '@/components/Admin/Charts/GeoChart.vue';
//import DevicesChart from '@/components/Admin/Charts/DevicesChart.vue';
//import ActivityChart from '@/components/Admin/Charts/ActivityChart.vue';
//import PopularRoomsTable from '@/components/Admin/Tables/PopularRoomsTable.vue';
//import RecentRegistrationsTable from '@/components/Admin/Tables/RecentRegistrationsTable.vue';
import AdminService from '@/API/Admin/AdminService';

const stats = ref({
	totalUsers: 0,
	onlineUsers: 0,
	activeRooms: 0,
	newToday: 0,
	genderData: [],
	geoData: [],
	devicesData: [],
	activityData: [],
	popularRooms: [],
	recentUsers: []
});

onMounted(async () => {
	try {
		const response = await AdminService.getDashboardStats();
		stats.value = response.data;
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