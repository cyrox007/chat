<template>
	<div class="devices-chart">
		<div class="header">
			<h4>Устройства</h4>
			<div class="active-devices">
				<span>Активных: </span>
				<strong>{{ data.active_now }}</strong>
			</div>
		</div>

		<div class="tabs">
			<button v-for="tab in tabs" :key="tab.id" :class="{ active: activeTab === tab.id }"
				@click="activeTab = tab.id">
				{{ tab.label }}
			</button>
		</div>

		<div class="chart-container">
			<!-- Добавлен общий контейнер для всех графиков -->
			<div class="chart-holder">
				<div v-show="activeTab === 'browsers'" class="tab-content">
					<canvas ref="browsersChart"></canvas>
				</div>
				<div v-show="activeTab === 'os'" class="tab-content">
					<canvas ref="osChart"></canvas>
				</div>
				<div v-show="activeTab === 'types'" class="tab-content">
					<canvas ref="typesChart"></canvas>
				</div>
				<div v-show="activeTab === 'brands'" class="tab-content">
					<canvas ref="brandsChart"></canvas>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
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

const tabs = [
	{ id: 'browsers', label: 'Браузеры' },
	{ id: 'os', label: 'ОС' },
	{ id: 'types', label: 'Типы' },
	{ id: 'brands', label: 'Бренды' }
];
const activeTab = ref('browsers');

const browsersChart = ref(null);
const osChart = ref(null);
const typesChart = ref(null);
const brandsChart = ref(null);

let browsersChartInstance = null;
let osChartInstance = null;
let typesChartInstance = null;
let brandsChartInstance = null;

// Функция для вычисления оптимального размера шрифта
const getFontSize = (dataLength) => {
	if (dataLength > 8) return 9;
	if (dataLength > 5) return 10;
	return 11;
};

const initChart = (chartRef, data) => {
	if (!chartRef.value || !data || data.length === 0) return null;

	const ctx = chartRef.value.getContext('2d');
	return new Chart(ctx, {
		type: 'pie',
		data: {
			labels: data.map(item => item.name || 'Unknown'),
			datasets: [{
				data: data.map(item => item.count),
				backgroundColor: [
					'#3a86ff', '#8338ec', '#ff006e', '#fb5607',
					'#ffbe0b', '#4cc9f0', '#f72585', '#7209b7',
					'#4361ee', '#3a0ca3', '#4895ef', '#4cc9f0'
				],
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
						boxWidth: 10,
						padding: 8,
						font: {
							size: getFontSize(data.length)
						},
						usePointStyle: true,
						pointStyle: 'circle'
					}
				}
			},
			layout: {
				padding: {
					left: 5,
					right: 5,
					top: 5,
					bottom: 5
				}
			}
		}
	});
};

const initCharts = async () => {
	// Ждем обновления DOM перед инициализацией
	await nextTick();

	[browsersChartInstance, osChartInstance, typesChartInstance, brandsChartInstance].forEach(
		chart => chart && chart.destroy()
	);

	browsersChartInstance = initChart(browsersChart, props.data.browsers);
	osChartInstance = initChart(osChart, props.data.os);
	typesChartInstance = initChart(typesChart, props.data.device_types);
	brandsChartInstance = initChart(brandsChart, props.data.brands);
};

onMounted(initCharts);
watch(() => props.data, initCharts, { deep: true });
watch(activeTab, initCharts);
</script>

<style scoped>
.devices-chart {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: white;
	border-radius: 8px;
	padding: 16px;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 12px;
}

.header h4 {
	margin: 0;
	font-size: 14px;
	color: #444;
	font-weight: 600;
}

.active-devices {
	font-size: 13px;
	color: #666;
}

.active-devices strong {
	color: #3a86ff;
	font-weight: 600;
}

.tabs {
	display: flex;
	gap: 4px;
	margin-bottom: 12px;
}

.tabs button {
	padding: 6px 12px;
	background: #f5f5f5;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 12px;
	color: #666;
	transition: all 0.2s;
}

.tabs button:hover {
	background: #e0e0e0;
}

.tabs button.active {
	background: #3a86ff;
	color: white;
}

.chart-container {
	flex: 1;
	min-height: 200px;
	position: relative;
}

.chart-holder {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
}

.tab-content {
	position: absolute;
	width: 100%;
	height: 100%;
}

.tab-content canvas {
	width: 100% !important;
	height: 100% !important;
	display: block;
}
</style>