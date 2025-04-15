<template>
    <div class="loader-container" v-if="isLoading">
        <div class="loader">
            <div class="spinner"></div>
            <p>{{ message }}</p>
        </div>
    </div>
</template>

<script setup>
import { defineProps } from "vue";
defineProps({
    isLoading: {
        type: Boolean,
        default: false,
    },
    message: {
        type: String,
        default: "Загрузка данных...",
    },
});
</script>

<style scoped>
.loader-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    background-color: aliceblue;
}

.loader {
    text-align: center;
}

.spinner {
    border: 4px solid rgba(0, 0, 0, 0.1);
    border-left-color: #007bff;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: 0 auto 10px;
}

@keyframes spin {
    0% {
        transform: rotate(0deg);
    }

    100% {
        transform: rotate(360deg);
    }
}

.loader p {
    font-size: 1.2rem;
    color: #888;
    font-style: italic;
}
</style>