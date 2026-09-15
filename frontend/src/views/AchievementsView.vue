<template>
	<main class="achievements-shell">
		<header class="achievements-hero">
			<div>
				<span class="eyebrow">История участия</span>
				<h1>Достижения без рейтинговой гонки</h1>
				<p>PubChat отмечает первые шаги и вклад в общение. Эти отметки не дают прав, trust, ранга или преимуществ в discovery.</p>
			</div>
			<RouterLink class="ui-button ui-button--ghost" :to="profileRoute">К моему образу</RouterLink>
		</header>

		<section v-if="loading" class="state-card" role="status">Загружаем историю…</section>
		<section v-else-if="errorMessage" class="state-card state-card--error" role="alert">
			<strong>Не удалось загрузить достижения</strong><span>{{ errorMessage }}</span>
			<button class="ui-button" type="button" @click="load">Повторить</button>
		</section>
		<section v-else-if="items.length" class="timeline" aria-label="История достижений">
			<article v-for="item in items" :key="`${item.code}-${item.earned_at}`" class="timeline-item">
				<span class="achievement-icon" aria-hidden="true"><i :class="iconClass(item.icon_preset)"></i></span>
				<div class="timeline-copy">
					<div class="timeline-title"><strong>{{ item.title }}</strong><span>{{ categoryLabel(item.category) }}</span></div>
					<p>{{ item.description }}</p>
					<small>{{ formatDate(item.earned_at) }} · {{ sourceLabel(item.source_kind) }}</small>
					<RouterLink v-if="item.context_space_uid" class="context-link" :to="{ name: 'space-life', params: { uid: item.context_space_uid } }">Открыть связанное пространство</RouterLink>
				</div>
			</article>
		</section>
		<section v-else class="state-card">
			<strong>Первые отметки ещё впереди</strong>
			<span>Создайте активность или поддержите разговорный раунд — достижения появятся автоматически.</span>
		</section>
	</main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useStore } from 'vuex';

import AchievementService from '@/API/AchievementService';

const store = useStore();
const loading = ref(true);
const errorMessage = ref('');
const items = ref([]);
const currentUser = computed(() => store.getters.getUser || {});
const profileRoute = computed(() => ({ name: 'UserProfile', params: { uid: currentUser.value.uid } }));

const iconClass = (preset) => ({
	'calendar-star': 'fas fa-calendar-plus',
	spark: 'fas fa-wand-magic-sparkles',
	'chat-heart': 'fas fa-comment-dots',
}[preset] || 'fas fa-sparkles');
const categoryLabel = (value) => ({ participation: 'Участие', conversation: 'Разговоры' }[value] || 'История');
const sourceLabel = (value) => ({
	activity_created: 'создана активность',
	conversation_round_created: 'начат разговорный раунд',
	conversation_round_response: 'поддержан разговор',
}[value] || 'отмечено системой');
const formatDate = (value) => value
	? new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
	: 'Дата не указана';

const load = async () => {
	loading.value = true;
	errorMessage.value = '';
	try {
		const response = await AchievementService.mine({ limit: 100 });
		items.value = response.data.achievements || [];
	} catch {
		errorMessage.value = 'Проверьте соединение и попробуйте ещё раз.';
	} finally {
		loading.value = false;
	}
};

onMounted(load);
</script>

<style scoped>
.achievements-shell { display: grid; gap: var(--ui-space-5); padding-bottom: var(--ui-space-8); }
.achievements-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--ui-space-6); padding: clamp(1.4rem,4vw,2.5rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: linear-gradient(135deg,var(--ui-surface),var(--ui-primary-soft)); }
.achievements-hero > div { max-width: 44rem; }.eyebrow { color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.achievements-hero h1 { margin: .35rem 0 0; font-size: clamp(1.8rem,4vw,2.8rem); line-height: 1.05; }.achievements-hero p { margin: var(--ui-space-3) 0 0; color: var(--ui-text-muted); line-height: 1.6; }
.timeline { display: grid; gap: var(--ui-space-3); }.timeline-item { display: grid; grid-template-columns: auto minmax(0,1fr); gap: var(--ui-space-4); padding: var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); box-shadow: var(--ui-shadow-sm); }
.achievement-icon { width: 3.1rem; height: 3.1rem; display: grid; place-items: center; border-radius: 1rem; background: var(--ui-primary-soft); color: var(--ui-primary); font-size: 1.15rem; }
.timeline-copy { min-width: 0; }.timeline-title { display: flex; gap: var(--ui-space-2); align-items: center; flex-wrap: wrap; }.timeline-title strong { font-size: var(--ui-text-lg); }.timeline-title span { padding: .2rem .5rem; border-radius: var(--ui-radius-pill); background: var(--ui-surface-muted); color: var(--ui-text-subtle); font-size: var(--ui-text-xs); font-weight: 700; }
.timeline-copy p { margin: .35rem 0; color: var(--ui-text-muted); }.timeline-copy small { color: var(--ui-text-subtle); }.context-link { display: inline-flex; margin-top: var(--ui-space-2); color: var(--ui-primary); font-size: var(--ui-text-sm); font-weight: 700; text-decoration: none; }
.state-card { display: grid; gap: .35rem; min-height: 12rem; place-content: center; padding: var(--ui-space-6); border: 1px dashed var(--ui-border); border-radius: var(--ui-radius-xl); text-align: center; color: var(--ui-text-muted); }.state-card strong { color: var(--ui-text); }.state-card .ui-button { justify-self: center; margin-top: var(--ui-space-2); }.state-card--error { border-color: color-mix(in srgb,var(--ui-danger) 35%,var(--ui-border)); }
@media (max-width: 640px) { .achievements-hero { align-items: stretch; flex-direction: column; }.achievements-hero .ui-button { width: 100%; }.timeline-item { grid-template-columns: 1fr; }.achievement-icon { width: 2.8rem; height: 2.8rem; } }
</style>
