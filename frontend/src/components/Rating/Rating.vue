<template>
    <div class="progress-container">
        <!-- Фоновая полоса -->
        <div class="progress-background">
            <!-- Полоса прогресса -->
            <div class="progress-bar" :style="barStyle">
                <!-- Частицы -->
                <div class="particles"></div>
            </div>
        </div>

        <!-- Волны -->
        <div class="waves-container">
            <svg class="waves" viewBox="0 0 100 10" preserveAspectRatio="none">
                <path fill="#2ecc71" d="M0 5 L100 5" />
                <path fill="#2ecc71" d="M0 5 C30 6 70 4 100 5" />
                <path fill="#2ecc71" d="M0 5 C20 6 80 4 100 5" />
                <path fill="#2ecc71" d="M0 5 C15 6 85 4 100 5" />
            </svg>
        </div>
    </div>
</template>

<script setup>
import { computed, defineProps } from 'vue';

// Props
const props = defineProps({
    rating: {
        type: Number,
        required: true,
    },
});

// Максимальное количество уровней
const MAX_LEVELS = 12;

// Границы уровней (геометрическая прогрессия)
const levelThresholds = Array.from({ length: MAX_LEVELS }, (_, i) => 5 ** (i + 1));

// Текущий уровень
const currentLevel = computed(() => {
    for (let i = 0; i < levelThresholds.length; i++) {
        if (props.rating < levelThresholds[i]) return i + 1;
    }
    return MAX_LEVELS; // Если рейтинг выше последнего порога
});

// Следующий уровень
const nextLevelThreshold = computed(() => levelThresholds[currentLevel.value]);

// Процент заполнения текущего уровня
const percentageToNextLevel = computed(() => {
    const currentThreshold = levelThresholds[currentLevel.value - 1] || 0;
    return Math.min(((props.rating - currentThreshold) / (nextLevelThreshold.value - currentThreshold)) * 100, 100);
});

// Цвета для уровней
const levelColors = [
    '#ff5733', // Красный (1 уровень)
    '#f39c12', // Желтый (2 уровень)
    '#2ecc71', // Зеленый (3 уровень)
    '#3498db', // Голубой (4 уровень)
    '#9b59b6', // Фиолетовый (5 уровень)
    '#8e44ad', // Темно-фиолетовый (6 уровень)
    '#e67e22', // Оранжевый (7 уровень)
    '#d35400', // Темно-оранжевый (8 уровень)
    '#1abc9c', // Бирюзовый (9 уровень)
    '#2980b9', // Темно-синий (10 уровень)
    '#7f8c8d', // Серый (11 уровень)
    '#2c3e50', // Темно-серый (12 уровень)
];

// Цвет текущего уровня
const currentColor = computed(() => levelColors[currentLevel.value - 1]);

// Цвет следующего уровня
const nextColor = computed(() => levelColors[currentLevel.value] || currentColor.value);

// Градиент для фона полосы прогресса
const gradientBackground = computed(() => {
    const progress = percentageToNextLevel.value / 100;
    return `linear-gradient(90deg, ${currentColor.value} ${progress * 100}%, ${nextColor.value} ${progress * 100}%)`;
});

// Интенсивность пульсации
const animationIntensity = computed(() => {
    const progress = percentageToNextLevel.value / 100;
    if (progress >= 1) return 'low'; // Пульсация стихает при достижении уровня
    if (progress > 0.8) return 'intense';
    if (progress > 0.5) return 'medium';
    return 'low';
});

// Стили для полосы прогресса
const barStyle = computed(() => ({
    width: `${percentageToNextLevel.value}%`,
    background: gradientBackground.value,
    transition: 'width 0.5s ease, background 0.5s ease',
}));
</script>

<style scoped>
/* Общий контейнер */
.progress-container {
    position: relative;
    width: 100%;
}

/* Фоновая полоса */
.progress-background {
    width: 100%;
    height: 20px; /* Высота полосы */
    position: relative;
    overflow: hidden;
    border-radius: 5px;
}

/* Полоса прогресса */
.progress-bar {
    height: 100%;
    border-radius: 5px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.3); /* Тень для объемности */
    animation: pulseBorder 2s ease-in-out infinite; /* Пульсация границ */
}

/* Анимация пульсации границ */
@keyframes pulseBorder {
    0%, 100% {
        box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
    }
    50% {
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.6);
    }
}

/* Частицы */
.particles {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: repeating-radial-gradient(
        circle at center,
        rgba(255, 255, 255, 0.7),
        rgba(255, 255, 255, 0.7) 5px,
        transparent 5px,
        transparent 10px
    );
    background-size: 20px 20px;
    animation: moveParticles 2s linear infinite;
}

/* Анимация движения частиц */
@keyframes moveParticles {
    0% {
        transform: translateX(0) translateY(0);
    }
    100% {
        transform: translateX(-20px) translateY(calc(-50% + 10px));
    }
}

/* Эффекты для высоких уровней */
.particles.level-10,
.particles.level-11,
.particles.level-12 {
    background: repeating-linear-gradient(
        45deg,
        rgba(255, 255, 255, 0.7),
        rgba(255, 255, 255, 0.7) 5px,
        transparent 5px,
        transparent 10px
    );
}

/* Волны */
.waves-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: -1;
}

.waves {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
}
</style>