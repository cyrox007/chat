<template>
	<div class="activity-chart">
		<canvas ref="chartCanvas"></canvas>
	</div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import Chart from 'chart.js/auto';

const props = defineProps({
	data: {
		type: Array,
		required: true
	}
});

const chartCanvas = ref(null);
let chartInstance = null;

const initChart = () => {
	if (chartInstance) {
		chartInstance.destroy();
	}

	const ctx = chartCanvas.value.getContext('2d');
	chartInstance = new Chart(ctx, {
		type: 'line',
		data: {
			labels: props.data.map(item => `${item.hour}:00`),
			datasets: [{
				label: 'Активность пользователей',
				data: props.data.map(item => item.count),
				borderColor: '#3A84FF',
				fill: true,
				tension: 0.1
			}]
		},
		options: {
			responsive: true,
			scales: {
				y: {
					beginAtZero: true
				}
			}
		}
	});
};

onMounted(initChart);
watch(() => props.data, initChart);
</script>