<template>
	<section class="round-panel">
		<button class="round-toggle" type="button" :aria-expanded="expanded" @click="toggle">
			<span><i class="fas fa-comments" aria-hidden="true"></i>Разговорный раунд</span>
			<small>{{ summary }}</small>
			<i :class="expanded ? 'fas fa-chevron-up' : 'fas fa-chevron-down'" aria-hidden="true"></i>
		</button>

		<div v-if="expanded" class="round-body">
			<div v-if="loading" class="round-state" role="status">Загружаем разговор…</div>
			<div v-else-if="errorMessage" class="round-state round-state--error">{{ errorMessage }}</div>
			<template v-else>
				<article v-if="openRound" class="round-card">
					<header class="round-head">
						<div><span>{{ roundTypeLabel(openRound.round_type) }}</span><strong>{{ openRound.prompt }}</strong></div>
						<button v-if="openRound.can_manage" type="button" class="text-button" @click="closeCurrentRound">Завершить</button>
					</header>

					<div v-if="openRound.round_type === 'choice'" class="choice-grid">
						<button type="button" :class="{ active: openRound.viewer_response?.choice === 'a' }" @click="respondChoice('a')">
							<strong>{{ openRound.option_a }}</strong><small>{{ openRound.choice_counts?.a || 0 }} выбрали</small>
						</button>
						<button type="button" :class="{ active: openRound.viewer_response?.choice === 'b' }" @click="respondChoice('b')">
							<strong>{{ openRound.option_b }}</strong><small>{{ openRound.choice_counts?.b || 0 }} выбрали</small>
						</button>
					</div>

					<form v-else class="response-form" @submit.prevent="respondText">
						<textarea v-model.trim="responseBody" maxlength="500" rows="3" :placeholder="openRound.round_type === 'story_chain' ? 'Продолжите историю своим фрагментом…' : 'Ваш ответ…'"></textarea>
						<div><small>До 500 символов · без очков и победителей</small><button class="ui-button" type="submit" :disabled="responding || responseBody.length < 2">{{ openRound.viewer_response ? 'Обновить ответ' : 'Ответить' }}</button></div>
					</form>

					<div class="responses-head">
						<span>{{ openRound.response_count }} {{ responseWord(openRound.response_count) }}</span>
						<button type="button" class="text-button" @click="loadResponses">{{ responsesLoaded ? 'Обновить' : 'Показать ответы' }}</button>
					</div>
					<div v-if="responsesLoaded" class="responses-list">
						<article v-for="response in responses" :key="response.account_uid" class="response-item">
							<span class="response-avatar">{{ avatarFallback(response.persona?.display_name || response.persona?.handle) }}</span>
							<div><strong>{{ response.persona?.display_name || response.persona?.handle || 'Участник' }}</strong><p>{{ response.choice ? choiceLabel(response.choice) : response.body }}</p></div>
						</article>
						<div v-if="!responses.length" class="round-state">Пока никто не ответил. Можно начать первым.</div>
					</div>
				</article>

				<div v-else-if="canCreateRound" class="round-create">
					<div><strong>Начать разговор</strong><p>Один активный раунд на встречу. Он помогает разговориться, а не определяет победителя.</p></div>
					<button v-if="!showCreateForm" class="ui-button" type="button" @click="showCreateForm = true">Создать раунд</button>
					<form v-else class="create-form" @submit.prevent="create">
						<label>Формат<select v-model="draft.round_type"><option value="icebreaker">Разогрев</option><option value="choice">Выбор без победителя</option><option value="story_chain">Общая история</option></select></label>
						<label class="wide">Тема<input v-model.trim="draft.prompt" maxlength="500" required placeholder="Например: Какой маленький ритуал делает вечер лучше?" /></label>
						<template v-if="draft.round_type === 'choice'">
							<label>Вариант A<input v-model.trim="draft.option_a" maxlength="120" required /></label>
							<label>Вариант B<input v-model.trim="draft.option_b" maxlength="120" required /></label>
						</template>
						<div class="wide create-actions"><button type="button" class="text-button" @click="showCreateForm = false">Отмена</button><button class="ui-button" type="submit" :disabled="creating">{{ creating ? 'Создаём…' : 'Открыть раунд' }}</button></div>
					</form>
				</div>

				<div v-else class="round-state">Активного разговорного раунда сейчас нет.</div>

				<details v-if="closedRounds.length" class="round-history">
					<summary>Прошлые раунды · {{ closedRounds.length }}</summary>
					<div v-for="round in closedRounds.slice(0, 5)" :key="round.uid"><strong>{{ round.prompt }}</strong><small>{{ round.response_count }} {{ responseWord(round.response_count) }}</small></div>
				</details>
			</template>
		</div>
	</section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';

import ConversationRoundService from '@/API/ConversationRoundService';

const props = defineProps({
	activity: { type: Object, required: true },
	canManageSpace: { type: Boolean, default: false },
	currentAccountUid: { type: String, default: '' },
});

const expanded = ref(false);
const loading = ref(false);
const errorMessage = ref('');
const rounds = ref([]);
const responses = ref([]);
const responsesLoaded = ref(false);
const responding = ref(false);
const creating = ref(false);
const showCreateForm = ref(false);
const responseBody = ref('');
const draft = reactive({ round_type: 'icebreaker', prompt: '', option_a: '', option_b: '' });

const openRound = computed(() => rounds.value.find((item) => item.status === 'open') || null);
const closedRounds = computed(() => rounds.value.filter((item) => item.status === 'closed'));
const canCreateRound = computed(() => props.activity.status === 'scheduled' && (props.canManageSpace || props.activity.created_by_account_uid === props.currentAccountUid));
const summary = computed(() => openRound.value ? `${openRound.value.response_count} ${responseWord(openRound.value.response_count)}` : 'без очков и рейтинга');

const roundTypeLabel = (value) => ({ icebreaker: 'Разогрев', choice: 'Выбор', story_chain: 'Общая история' }[value] || 'Разговор');
const responseWord = (count) => count % 10 === 1 && count % 100 !== 11 ? 'ответ' : (count % 10 >= 2 && count % 10 <= 4 && !(count % 100 >= 12 && count % 100 <= 14) ? 'ответа' : 'ответов');
const avatarFallback = (value = '?') => String(value || '?').slice(0, 1).toUpperCase();
const choiceLabel = (choice) => choice === 'a' ? openRound.value?.option_a : openRound.value?.option_b;

const load = async () => {
	loading.value = true;
	errorMessage.value = '';
	try {
		const response = await ConversationRoundService.list(props.activity.uid);
		rounds.value = response.data.rounds || [];
		responseBody.value = openRound.value?.viewer_response?.body || '';
		responsesLoaded.value = false;
		responses.value = [];
	} catch {
		errorMessage.value = 'Не удалось загрузить разговорный раунд.';
	} finally {
		loading.value = false;
	}
};
const toggle = async () => { expanded.value = !expanded.value; if (expanded.value) await load(); };

const loadResponses = async () => {
	if (!openRound.value) return;
	try {
		const response = await ConversationRoundService.responses(openRound.value.uid, { limit: 100 });
		responses.value = response.data.responses || [];
		responsesLoaded.value = true;
	} catch { errorMessage.value = 'Не удалось загрузить ответы.'; }
};

const create = async () => {
	creating.value = true;
	errorMessage.value = '';
	try {
		const payload = { round_type: draft.round_type, prompt: draft.prompt, option_a: null, option_b: null };
		if (draft.round_type === 'choice') { payload.option_a = draft.option_a; payload.option_b = draft.option_b; }
		await ConversationRoundService.create(props.activity.uid, payload);
		Object.assign(draft, { round_type: 'icebreaker', prompt: '', option_a: '', option_b: '' });
		showCreateForm.value = false;
		await load();
	} catch (error) {
		errorMessage.value = error.response?.data?.detail?.error_type === 'conversation_round_already_open' ? 'У этой активности уже есть открытый раунд.' : 'Не удалось создать раунд.';
	} finally { creating.value = false; }
};

const respondChoice = async (choice) => {
	if (!openRound.value || responding.value) return;
	responding.value = true;
	try { await ConversationRoundService.respond(openRound.value.uid, { choice, body: null }); await load(); if (responsesLoaded.value) await loadResponses(); }
	catch { errorMessage.value = 'Не удалось сохранить ответ.'; }
	finally { responding.value = false; }
};
const respondText = async () => {
	if (!openRound.value || responseBody.value.length < 2 || responding.value) return;
	responding.value = true;
	try { await ConversationRoundService.respond(openRound.value.uid, { choice: null, body: responseBody.value }); await load(); await loadResponses(); }
	catch { errorMessage.value = 'Не удалось сохранить ответ.'; }
	finally { responding.value = false; }
};
const closeCurrentRound = async () => {
	if (!openRound.value) return;
	try { await ConversationRoundService.close(props.activity.uid, openRound.value.uid); await load(); }
	catch { errorMessage.value = 'Не удалось завершить раунд.'; }
};

watch(() => props.activity.uid, () => { expanded.value = false; rounds.value = []; responses.value = []; });
</script>

<style scoped>
.round-panel { grid-column: 1 / -1; border-top: 1px solid var(--ui-border); padding-top: var(--ui-space-3); }
.round-toggle { width: 100%; min-height: 2.5rem; display: grid; grid-template-columns: minmax(0,1fr) auto auto; align-items: center; gap: var(--ui-space-2); border: 0; background: transparent; color: var(--ui-text); text-align: left; cursor: pointer; }.round-toggle > span { display: inline-flex; align-items: center; gap: var(--ui-space-2); font-weight: 750; }.round-toggle > span i { color: var(--ui-primary); }.round-toggle small { color: var(--ui-text-subtle); }
.round-body { display: grid; gap: var(--ui-space-3); padding-top: var(--ui-space-3); }.round-card,.round-create { display: grid; gap: var(--ui-space-3); padding: var(--ui-space-4); border-radius: var(--ui-radius-lg); background: var(--ui-surface-muted); }.round-head { display: flex; justify-content: space-between; gap: var(--ui-space-3); }.round-head > div { display: grid; gap: .25rem; }.round-head span { color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; text-transform: uppercase; letter-spacing: .05em; }.round-head strong { font-size: var(--ui-text-lg); }
.text-button { border: 0; background: transparent; color: var(--ui-primary); font: inherit; font-size: var(--ui-text-sm); font-weight: 700; cursor: pointer; }.choice-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: var(--ui-space-2); }.choice-grid button { min-height: 4.5rem; display: grid; gap: .3rem; place-content: center; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface); color: var(--ui-text); cursor: pointer; }.choice-grid button.active { border-color: var(--ui-primary); background: var(--ui-primary-soft); }.choice-grid small { color: var(--ui-text-muted); }
.response-form { display: grid; gap: var(--ui-space-2); }.response-form textarea,.create-form input,.create-form select { width: 100%; padding: .75rem; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text); font: inherit; }.response-form > div { display: flex; align-items: center; justify-content: space-between; gap: var(--ui-space-2); }.response-form small { color: var(--ui-text-subtle); }.responses-head { display: flex; align-items: center; justify-content: space-between; gap: var(--ui-space-2); color: var(--ui-text-muted); font-size: var(--ui-text-sm); }.responses-list { display: grid; gap: var(--ui-space-2); }.response-item { display: grid; grid-template-columns: auto minmax(0,1fr); gap: var(--ui-space-2); padding: var(--ui-space-2); border-radius: var(--ui-radius-md); background: var(--ui-surface); }.response-avatar { width: 2rem; height: 2rem; display: grid; place-items: center; border-radius: 50%; background: var(--ui-primary-soft); color: var(--ui-primary); font-weight: 800; }.response-item strong { font-size: var(--ui-text-sm); }.response-item p { margin: .2rem 0 0; color: var(--ui-text-muted); font-size: var(--ui-text-sm); white-space: pre-wrap; }
.round-create > div p { margin: .3rem 0 0; color: var(--ui-text-muted); }.create-form { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: var(--ui-space-3); }.create-form label { display: grid; gap: .35rem; color: var(--ui-text-muted); font-size: var(--ui-text-sm); font-weight: 700; }.wide { grid-column: 1 / -1; }.create-actions { display: flex; justify-content: flex-end; gap: var(--ui-space-2); }.round-state { padding: var(--ui-space-3); border: 1px dashed var(--ui-border); border-radius: var(--ui-radius-md); color: var(--ui-text-muted); }.round-state--error { color: var(--ui-danger); border-color: color-mix(in srgb,var(--ui-danger) 35%,var(--ui-border)); }.round-history { color: var(--ui-text-muted); font-size: var(--ui-text-sm); }.round-history summary { cursor: pointer; font-weight: 700; }.round-history > div { display: flex; justify-content: space-between; gap: var(--ui-space-2); padding: .6rem 0; border-bottom: 1px solid var(--ui-border); }.round-history small { color: var(--ui-text-subtle); }
@media (max-width: 640px) { .round-toggle { grid-template-columns: 1fr auto; }.round-toggle small { grid-column: 1 / -1; }.choice-grid,.create-form { grid-template-columns: 1fr; }.wide { grid-column: auto; }.response-form > div,.round-head { align-items: stretch; flex-direction: column; }.create-actions { flex-direction: column-reverse; }.create-actions .ui-button { width: 100%; } }
</style>
