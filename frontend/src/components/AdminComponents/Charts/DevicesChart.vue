<template>
	<div class="devices-chart">
		<div class="devices-stats">
			<div class="stat-item">
				<h4>Активных устройств</h4>
				<p class="stat-value">{{ data.active_now }}</p>
			</div>
		</div>

		<div class="charts-grid">
			<div class="chart-container">
				<h4>Браузеры</h4>
				<div class="chart-wrapper">
					<canvas ref="browsersChart"></canvas>
				</div>
			</div>

			<div class="chart-container">
				<h4>Операционные системы</h4>
				<div class="chart-wrapper">
					<canvas ref="osChart"></canvas>
				</div>
			</div>

			<div class="chart-container">
				<h4>Типы устройств</h4>
				<div class="chart-wrapper">
					<canvas ref="typesChart"></canvas>
				</div>
			</div>

			<div class="chart-container">
				<h4>Бренды</h4>
				<div class="chart-wrapper">
					<canvas ref="brandsChart"></canvas>
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
			browsers: [],
			os: [],
			device_types: [],
			brands: [],
			active_now: 0
		})
	}
});

const browsersChart = ref(null);
const osChart = ref(null);
const typesChart = ref(null);
const brandsChart = ref(null);

let browsersChartInstance = null;
let osChartInstance = null;
let typesChartInstance = null;
let brandsChartInstance = null;

const chartColors = [
	'#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
	'#9966FF', '#FF9F40', '#8AC24A', '#F06292',
	'#00ACC1', '#7E57C2', '#EC407A', '#AB47BC'
];

const initChart = (chartRef, data, title) => {
	if (!chartRef.value || !data || data.length === 0) return null;

	const ctx = chartRef.value.getContext('2d');
	return new Chart(ctx, {
		type: 'doughnut',
		data: {
			labels: data.map(item => item.name || 'Unknown'),
			datasets: [{
				data: data.map(item => item.count),
				backgroundColor: chartColors.slice(0, data.length),
				borderWidth: 1
			}]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			plugins: {
				legend: {
					position: 'right',
					labels: {
						boxWidth: 12,
						padding: 20
					}
				},
				title: {
					display: false,
					text: title
				}
			},
			cutout: '60%'
		}
	});
};

const initCharts = () => {
	// Destroy previous instances
	[browsersChartInstance, osChartInstance, typesChartInstance, brandsChartInstance].forEach(
		chart => chart && chart.destroy()
	);

	// Initialize new charts
	browsersChartInstance = initChart(browsersChart, props.data.browsers, 'Браузеры');
	osChartInstance = initChart(osChart, props.data.os, 'Операционные системы');
	typesChartInstance = initChart(typesChart, props.data.device_types, 'Типы устройств');
	brandsChartInstance = initChart(brandsChart, props.data.brands, 'Бренды');
};

onMounted(initCharts);
watch(() => props.data, initCharts, { deep: true });
</script>

<style scoped>
.devices-chart {
	display: flex;
	flex-direction: column;
	gap: 20px;
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
	min-width: 200px;
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

.charts-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
	gap: 20px;
	height: calc(100% - 60px);
}

.chart-container {
	display: flex;
	flex-direction: column;
	background: white;
	border-radius: 8px;
	padding: 16px;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	height: 300px;
}

.chart-container h4 {
	margin: 0 0 12px 0;
	font-size: 14px;
	text-align: center;
	color: #444;
	font-weight: 500;
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

@media (max-width: 1400px) {
	.charts-grid {
		grid-template-columns: 1fr 1fr;
	}
}

@media (max-width: 768px) {
	.charts-grid {
		grid-template-columns: 1fr;
	}

	.chart-container {
		height: 250px;
	}
}
</style>