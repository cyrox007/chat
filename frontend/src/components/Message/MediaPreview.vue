<template>
	<div class="media-preview" :class="type">
		<img v-if="type.includes('image')" :src="file.url" :alt="file.name" @load="onLoaded" />
		<video v-else-if="type.includes('video')" controls>
			<source :src="file.url" :type="file.type" />
		</video>
		<div v-else class="file-preview">
			<i class="fas fa-file"></i>
			<span>{{ file.name }}</span>
			<span class="file-size">{{ formatFileSize(file.size) }}</span>
		</div>
	</div>
</template>

<script setup>
import { defineProps } from "vue";
const props = defineProps({
	file: Object,
	type: String
});

const onLoaded = () => {
	// Оптимизация загрузки медиа
};

const formatFileSize = (bytes) => {
	if (bytes === 0) return '0 Bytes';
	const k = 1024;
	const sizes = ['Bytes', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
</script>