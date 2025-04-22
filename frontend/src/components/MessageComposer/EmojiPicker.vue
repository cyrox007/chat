<template>
	<div class="emoji-picker-wrapper" v-if="props.isShow" >
		<!-- <button class="emoji-trigger" @click="togglePicker">
			<i class="far fa-smile"></i>
		</button> -->

		<div  class="emoji-picker">
			<div class="emoji-search" v-if="withSearch">
				<input v-model="searchQuery" placeholder="Поиск смайлов..." @input="filterEmojis" />
			</div>

			<div class="emoji-categories">
				<button v-for="category in categories" :key="category.name" @click="setActiveCategory(category.name)"
					:class="{ active: activeCategory === category.name }">
					{{ category.icon }}
				</button>
			</div>

			<div class="emoji-list">
				<div v-for="emoji in filteredEmojis" :key="emoji">
					<button class="emoji-item" @click="selectEmoji(emoji)" :title="getEmojiName(emoji)">
						{{ emoji }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

// Пропсы
const props = defineProps({
	withSearch: {
		type: Boolean,
		default: true
	},
	isShow: {
		type: Boolean,
		default: false
	}
});

const emit = defineEmits(['emoji-selected']);

// Состояние
const showPicker = ref(false);
const searchQuery = ref('');
const activeCategory = ref('people');
const emojiData = ref({});

// Категории emoji
const categories = [
	{ name: 'people', icon: '😀' },
	{ name: 'nature', icon: '🐻' },
	{ name: 'food', icon: '🍎' },
	{ name: 'activities', icon: '⚽' },
	{ name: 'travel', icon: '🚗' },
	{ name: 'objects', icon: '💡' },
	{ name: 'symbols', icon: '❤️' },
	{ name: 'flags', icon: '🇷🇺' }
];

// Основной набор emoji (можно расширить)
const baseEmojis = {
	people: ['😀', '😂', '😊', '😍', '😎', '😜', '🤔', '😴', '😷', '🤧'],
	nature: ['🐻', '🐶', '🐱', '🦁', '🐮', '🐷', '🐸', '🐥', '🦄', '🐝'],
	food: ['🍎', '🍕', '🍔', '🍟', '🍦', '🍩', '🍪', '🍫', '🍓', '🍉'],
	activities: ['⚽', '🏀', '🎾', '🏓', '🎯', '🎮', '🎲', '🎸', '🎨', '🎭'],
	travel: ['🚗', '✈️', '🚀', '⛵', '🚲', '🏎️', '🚂', '🚁', '🛴', '🚢'],
	objects: ['💡', '📱', '💻', '⌚', '📷', '🔑', '🎁', '📦', '🛏️', '🛋️'],
	symbols: ['❤️', '👍', '👎', '🙏', '✌️', '🤝', '💪', '👀', '👃', '👂'],
	flags: ['🇷🇺', '🇺🇸', '🇬🇧', '🇩🇪', '🇫🇷', '🇨🇳', '🇯🇵', '🇰🇷', '🇮🇹', '🇪🇸']
};

// Инициализация данных emoji
onMounted(() => {
	// Можно загрузить более полный набор emoji при необходимости
	emojiData.value = baseEmojis;
});

// Фильтрация emoji
const filteredEmojis = computed(() => {
	if (!emojiData.value[activeCategory.value]) return [];

	return emojiData.value[activeCategory.value].filter(emoji => {
		if (!searchQuery.value) return true;
		const name = getEmojiName(emoji).toLowerCase();
		return name.includes(searchQuery.value.toLowerCase());
	});
});

const setActiveCategory = (category) => {
	activeCategory.value = category;
};

const selectEmoji = (emoji) => {
	emit('emoji-selected', emoji);
	showPicker.value = false;
};

const getEmojiName = (emoji) => {
	// Простая реализация - можно расширить словарем
	return emoji;
};

const filterEmojis = () => {
	// Автоматически обрабатывается в computed свойстве
};
</script>

<style scoped>
.emoji-picker-wrapper {
	position: relative;
	display: inline-block;
}

.emoji-trigger {
	background: none;
	border: none;
	cursor: pointer;
	font-size: 1.5rem;
	color: var(--text-light);
	padding: 5px;
	transition: color 0.2s;
}

.emoji-trigger:hover {
	color: var(--primary-color);
}

.emoji-picker {
	position: absolute;
	bottom: 50px;
	left: 0;
	width: 300px;
	max-height: 350px;
	background: var(--bg-light);
	border: 1px solid var(--messenger-border);
	border-radius: 8px;
	box-shadow: var(--shadow-medium);
	z-index: 1000;
	display: flex;
	flex-direction: column;
	padding: 10px;
}

.emoji-search {
	padding: 8px;
}

.emoji-search input {
	width: 100%;
	padding: 8px;
	border: 1px solid var(--messenger-border);
	border-radius: 4px;
	background: var(--messenger-input-bg);
	color: var(--text-light);
}

.emoji-categories {
	display: flex;
	padding: 8px 0;
	border-bottom: 1px solid var(--messenger-border);
	overflow-x: auto;
}

.emoji-categories button {
	background: none;
	border: none;
	cursor: pointer;
	font-size: 1.5rem;
	padding: 0 10px;
	opacity: 0.7;
}

.emoji-categories button.active {
	opacity: 1;
	transform: scale(1.1);
}

.emoji-list {
	display: grid;
	grid-template-columns: repeat(8, 1fr);
	gap: 5px;
	padding: 10px 0;
	overflow-y: auto;
	flex-grow: 1;
}

.emoji-item {
	background: none;
	border: none;
	cursor: pointer;
	font-size: 1.5rem;
	padding: 5px;
	border-radius: 4px;
	transition: all 0.2s;
}

.emoji-item:hover {
	background: var(--primary-color);
	transform: scale(1.2);
}

@media (max-width: 768px) {
	.emoji-picker {
		width: 280px;
		max-height: 300px;
		right: -50px;
	}

	.emoji-list {
		grid-template-columns: repeat(6, 1fr);
	}
}
</style>