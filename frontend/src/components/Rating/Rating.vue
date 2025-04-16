<template>
    <span>{{ props.rating || 'Рейтинга нет'}}</span>
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
</script>

<style scoped>

</style>