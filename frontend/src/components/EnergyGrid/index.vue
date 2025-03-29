<template>
    <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
        <defs>
            <linearGradient id="energyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#FF5722" />
                <stop offset="50%" stop-color="#FFC107" />
                <stop offset="100%" stop-color="#4CAF50" />
            </linearGradient>
        </defs>
        <g fill="url(#energyGradient)">
            <rect
                v-for="(cell, index) in cells"
                :key="index"
                :x="cell.x"
                :y="cell.y"
                width="20"
                height="20"
                rx="5"
                :opacity="cell.opacity"
            >
                <animate attributeName="opacity" values="0;1" dur="1s" repeatCount="1" />
            </rect>
        </g>
    </svg>
</template>

<script setup>
import { computed } from 'vue';

// Принимаем рейтинг как пропс
const props = defineProps({
    rating: {
        type: Number,
        required: true,
    },
});

// Вычисляем количество ячеек на основе рейтинга
const cells = computed(() => {
    const totalCells = Math.ceil(props.rating / 10); // 10 баллов = 1 ячейка
    const grid = [];
    for (let i = 0; i < totalCells; i++) {
        grid.push({
            x: (i % 10) * 25, // Расположение по горизонтали
            y: Math.floor(i / 10) * 25, // Расположение по вертикали
            opacity: 1,
        });
    }
    return grid;
});
</script>

<style scoped>
svg {
    display: block;
    margin: 0 auto;
}
</style>