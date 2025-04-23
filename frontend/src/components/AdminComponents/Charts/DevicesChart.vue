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
				<div class="chart-wrapper">
					<canvas ref="modelsChart"></canvas>
				</div>
			</div>
			<div class="chart-container">
				<h4>По типам</h4>
				<div class="chart-wrapper">
					<canvas ref="typesChart"></canvas>
				</div>
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
		required: true,
		default: () => ({
			by_model: [],
			by_type: [],
			active_now: 0
		})
	}
});

const modelsChart = ref(null);
const typesChart = ref(null);
let modelsChartInstance = null;
let typesChartInstance = null;

const initCharts = () => {
	// Destroy previous instances
	if (modelsChartInstance) modelsChartInstance.destroy();
	if (typesChartInstance) typesChartInstance.destroy();

	// Models chart
	if (props.data.by_model.length > 0) {
		modelsChartInstance = new Chart(modelsChart.value.getContext('2d'), {
			type: 'pie',
			data: {
				labels: props.data.by_model.map(item => item.device || 'Unknown'),
				datasets: [{
					data: props.data.by_model.map(item => item.count),
					backgroundColor: [
						'#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
						'#9966FF', '#FF9F40', '#8AC24A', '#F06292'
					]
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						position: 'bottom'
					}
				}
			}
		});
	}

	// Types chart
	if (props.data.by_type.length > 0) {
		typesChartInstance = new Chart(typesChart.value.getContext('2d'), {
			type: 'doughnut',
			data: {
				labels: props.data.by_type.map(item => item.type || 'Unknown'),
				datasets: [{
					data: props.data.by_type.map(item => item.count),
					backgroundColor: [
						'#FF9F40', '#9966FF', '#FFCD56', '#4CAF50',
						'#2196F3', '#9C27B0', '#00BCD4'
					]
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						position: 'bottom'
					}
				}
			}
		});
	}
};

onMounted(initCharts);
watch(() => props.data, initCharts, { deep: true });
</script>

<style scoped>
.devices-chart {
	display: flex;
	flex-direction: column;
	gap: 16px;
	height: 100%;
}

.devices-stats {
	display: flex;
	justify-content: center;
	margin-bottom: 8px;
}

.stat-item {
	text-align: center;
	padding: 8px 16px;
	background: #f5f5f5;
	border-radius: 8px;
}

.stat-item h4 {
	margin: 0 0 4px 0;
	font-size: 14px;
	color: #666;
}

.stat-value {
	margin: 0;
	font-size: 20px;
	font-weight: bold;
	color: #333;
}

.charts-row {
	display: flex;
	gap: 16px;
	height: calc(100% - 60px);
}

.chart-container {
	flex: 1;
	display: flex;
	flex-direction: column;
	background: white;
	border-radius: 8px;
	padding: 16px;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-container h4 {
	margin: 0 0 8px 0;
	font-size: 14px;
	text-align: center;
	color: #444;
}

.chart-wrapper {
	position: relative;
	flex: 1;
	min-height: 200px;
}

canvas {
	width: 100% !important;
	height: 100% !important;
}
</style>