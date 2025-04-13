<template>
    <div class="voice-message">
        <audio controls :src="audio.url"></audio>
        <!-- <span class="duration">{{ formatDuration(audio.duration) }}</span> -->
    </div>
</template>

<script setup>
const props = defineProps({
    audio: Object
});

const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
};
</script>