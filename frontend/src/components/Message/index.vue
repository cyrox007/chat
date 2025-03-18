<template>
    <div :class="['message', messageType]">
        <div class="message-header">
            <img :src="message.avatar" alt="Аватар" class="avatar" />
            <div class="user-info">
                <strong>{{ message.username }}:</strong>
                <span class="timestamp">{{ message.timestamp }}</span>
            </div>
        </div>
        <div class="message-body">
            <div v-if="message.type === 'text'">{{ message.content }}</div>
            <div v-if="message.type === 'image'">
                <img :src="message.content" alt="Изображение" class="message-image" />
                <span class="image-caption">{{ message.caption }}</span>
            </div>
            <div v-if="message.type === 'mention'">
                <span v-html="message.content"></span>
            </div>
            <div v-if="message.type === 'video'">
                <video controls class="message-video">
                    <source :src="message.content" type="video/mp4">
                    Ваш браузер не поддерживает видео.
                </video>
            </div>
            <div v-if="message.type === 'audio'">
                <audio controls class="message-audio">
                    <source :src="message.content" type="audio/mpeg">
                    Ваш браузер не поддерживает аудио.
                </audio>
            </div>
        </div>
    </div>
</template>

<script setup>
import { defineProps, computed } from 'vue';

const props = defineProps({
    message: {
        type: Object,
        required: true,
    },
});

const messageType = computed(() => {
    if (props.message.sender) {
        return 'sender';
    }
    if (props.message.type == 'mention') {
        return 'mention';
    }
    return 'other-user';
});
</script>

<style scoped>
/* Добавьте ваши стили здесь */
</style>