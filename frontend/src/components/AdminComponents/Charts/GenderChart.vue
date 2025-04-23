<template>
	<div class="chart-container">
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
		type: 'doughnut',
		data: {
			labels: props.data.map(item => item.gender),
			datasets: [{
				data: props.data.map(item => item.count),
				backgroundColor: [
					'#36A2EB',
					'#FF6384',
					'#FFCE56'
				]
			}]
		},
		options: {
			responsive: true,
			plugins: {
				legend: {
					position: 'bottom'
				}
			}
		}
	});
};

onMounted(initChart);
watch(() => props.data, initChart);
</script>

<style scoped>
.chart-container {
	position: relative;
	height: 300px;
}
</style>