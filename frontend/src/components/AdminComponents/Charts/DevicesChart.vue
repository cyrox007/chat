<template>
	<div class="devices-chart">
		<div class="devices-stats">
			<div class="stat-item">
				<h4>Активных устройств</h4>
				<p class="stat-value">{{ data.active_now }}</p>
			</div>
		</div>

		<div class="charts-row">
			<div class="chart-container">
				<h4>По моделям</h4>
				<canvas ref="modelsChart"></canvas>
			</div>
			<div class="chart-container">
				<h4>По типам</h4>
				<canvas ref="typesChart"></canvas>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import Chart from 'chart.js/auto';

const props = defineProps({
	data: {
		type: Object,
		required: true
	}
});

const modelsChart = ref(null);
const typesChart = ref(null);
let modelsChartInstance = null;
let typesChartInstance = null;

const initCharts = () => {
	// Инициализация графика по моделям
	if (modelsChartInstance) modelsChartInstance.destroy();
	modelsChartInstance = new Chart(modelsChart.value.getContext('2d'), {
		type: 'pie',
		data: {
			labels: props.data.by_model.map(item => item.device),
			datasets: [{
				data: props.data.by_model.map(item => item.count),
				backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
			}]
		}
	});

	// Инициализация графика по типам
	if (typesChartInstance) typesChartInstance.destroy();
	typesChartInstance = new Chart(typesChart.value.getContext('2d'), {
		type: 'doughnut',
		data: {
			labels: props.data.by_type.map(item => item.type),
			datasets: [{
				data: props.data.by_type.map(item => item.count),
				backgroundColor: ['#FF9F40', '#9966FF', '#FFCD56']
			}]
		}
	});
};

onMounted(initCharts);
watch(() => props.data, initCharts);
</script>

<style scoped>
.devices-chart {
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.devices-stats {
	display: flex;
	justify-content: center;
}

.stat-item {
	text-align: center;
}

.stat-value {
	font-size: 24px;
	font-weight: bold;
}

.charts-row {
	display: flex;
	gap: 20px;
}

.chart-container {
	flex: 1;
	height: 250px;
}
</style>