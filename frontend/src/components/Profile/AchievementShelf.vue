<template>
	<section class="achievement-shelf" aria-labelledby="achievement-shelf-title">
		<header class="shelf-head">
			<div>
				<p>История участия</p>
				<h2 id="achievement-shelf-title">Достижения</h2>
			</div>
			<RouterLink v-if="isSelf && total" :to="{ name: 'achievements' }">Вся история</RouterLink>
		</header>

		<div v-if="loading" class="shelf-state" role="status">Загружаем достижения…</div>
		<div v-else-if="items.length" class="achievement-grid">
			<article v-for="item in items" :key="`${item.code}-${item.earned_at}`" class="achievement-item">
				<span class="achievement-icon" aria-hidden="true"><i :class="iconClass(item.icon_preset)"></i></span>
				<div><strong>{{ item.title }}</strong><p>{{ item.description }}</p></div>
			</article>
		</div>
		<div v-else-if="!failed" class="shelf-state">
			<strong>История только начинается</strong>
			<span>Достижения отмечают участие и вклад, но не дают прав, ранга или преимуществ.</span>
		</div>
	</section>

	<SupportShelf :account-uid="accountUid" :is-self="isSelf" />
</template>

<script setup>
import { onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import AchievementService from '@/API/AchievementService';
import SupportShelf from '@/components/Profile/SupportShelf.vue';

const props = defineProps({
	accountUid: { type: String, required: true },
	isSelf: { type: Boolean, default: false },
});

const loading = ref(true);
const failed = ref(false);
const items = ref([]);
const total = ref(0);

const iconClass = (preset) => ({
	host: 'fas fa-mug-hot',
	conversation: 'fas fa-comments',
	response: 'fas fa-comment-dots',
}[preset] || 'fas fa-sparkles');

const load = async () => {
	if (!props.accountUid) return;
	loading.value = true;
	failed.value = false;
	try {
		const response = await AchievementService.publicForAccount(props.accountUid, { limit: 6 });
		items.value = response.data.achievements || [];
		total.value = response.data.pagination?.total || items.value.length;
	} catch {
		items.value = [];
		total.value = 0;
		failed.value = true;
	} finally { loading.value = false; }
};

watch(() => props.accountUid, load);
onMounted(load);
</script>

<style scoped>
.achievement-shelf { display: grid; gap: var(--ui-space-4); padding: clamp(1rem,3vw,1.5rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); box-shadow: var(--ui-shadow-sm); }
.shelf-head { display: flex; align-items: end; justify-content: space-between; gap: var(--ui-space-3); }
.shelf-head p { margin: 0; color: var(--ui-text-subtle); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.shelf-head h2 { margin: .2rem 0 0; font-size: var(--ui-text-lg); }
.shelf-head a { color: var(--ui-primary); font-size: var(--ui-text-sm); font-weight: 750; text-decoration: none; }
.achievement-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: var(--ui-space-2); }
.achievement-item { min-width: 0; display: grid; grid-template-columns: auto minmax(0,1fr); gap: var(--ui-space-3); align-items: start; padding: var(--ui-space-3); border-radius: var(--ui-radius-lg); background: var(--ui-surface-muted); }
.achievement-icon { width: 2.6rem; height: 2.6rem; display: grid; place-items: center; border-radius: .9rem; background: var(--ui-primary-soft); color: var(--ui-primary); }
.achievement-item strong { display: block; font-size: var(--ui-text-sm); }
.achievement-item p { margin: .25rem 0 0; color: var(--ui-text-muted); font-size: var(--ui-text-xs); line-height: 1.45; }
.shelf-state { display: grid; gap: .25rem; padding: var(--ui-space-4); border: 1px dashed var(--ui-border); border-radius: var(--ui-radius-lg); color: var(--ui-text-muted); }
.shelf-state strong { color: var(--ui-text); }
@media (max-width: 640px) { .achievement-grid { grid-template-columns: 1fr; }.shelf-head { align-items: start; } }
</style>
