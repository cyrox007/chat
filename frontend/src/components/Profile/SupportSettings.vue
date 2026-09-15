<template>
	<section class="support-settings">
		<header>
			<div><span class="eyebrow">Поддержка Persona</span><h2>Разрешить тёплые знаки внимания</h2></div>
			<label class="switch-row"><input v-model="enabled" type="checkbox" /><span>{{ enabled ? 'Включено' : 'Выключено' }}</span></label>
		</header>
		<p>Это бесплатные cosmetic gifts. Они не влияют на доверие, права, рекомендации или модерацию.</p>
		<label class="note-field">Короткое пояснение
			<input v-model.trim="note" maxlength="280" :disabled="!enabled" placeholder="Например: Если вам было уютно общаться — можно оставить знак внимания" />
		</label>
		<div class="actions">
			<span v-if="notice" :class="['notice', `notice--${notice.type}`]">{{ notice.message }}</span>
			<button class="ui-button" type="button" :disabled="saving" @click="save">{{ saving ? 'Сохраняем…' : 'Сохранить' }}</button>
		</div>
		<div v-if="received.length" class="history">
			<strong>Последние полученные</strong>
			<article v-for="entry in received" :key="entry.uid">
				<span class="icon" aria-hidden="true">{{ entry.gift.icon }}</span>
				<div><strong>{{ entry.gift.name }}</strong><small>{{ entry.sender_label || 'Persona PubChat' }}<template v-if="entry.message"> · {{ entry.message }}</template></small></div>
			</article>
		</div>
	</section>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import SupportService from '@/API/SupportService';

const enabled = ref(false);
const note = ref('');
const saving = ref(false);
const notice = ref(null);
const received = ref([]);

const load = async () => {
	try {
		const [profileResponse, historyResponse] = await Promise.all([
			SupportService.myProfile(),
			SupportService.myReceived({ limit: 8 }),
		]);
		enabled.value = Boolean(profileResponse.data.support?.enabled);
		note.value = profileResponse.data.support?.note || '';
		received.value = historyResponse.data.items || [];
	} catch {
		notice.value = { type: 'error', message: 'Не удалось загрузить настройки поддержки.' };
	}
};

const save = async () => {
	saving.value = true; notice.value = null;
	try {
		const response = await SupportService.updateMyProfile({ enabled: enabled.value, note: enabled.value ? note.value || null : null });
		enabled.value = Boolean(response.data.support?.enabled);
		note.value = response.data.support?.note || '';
		notice.value = { type: 'success', message: enabled.value ? 'Получение gifts включено.' : 'Получение gifts выключено.' };
	} catch { notice.value = { type: 'error', message: 'Не удалось сохранить настройки.' }; }
	finally { saving.value = false; }
};

onMounted(load);
</script>

<style scoped>
.support-settings{display:grid;gap:var(--ui-space-4);padding:var(--ui-space-5);border:1px solid var(--ui-border);border-radius:var(--ui-radius-xl);background:var(--ui-surface)}.support-settings header{display:flex;align-items:center;justify-content:space-between;gap:var(--ui-space-4)}.support-settings h2{margin:.2rem 0 0;font-size:var(--ui-text-xl)}.eyebrow{color:var(--ui-primary);font-size:var(--ui-text-xs);font-weight:800;letter-spacing:.08em;text-transform:uppercase}.support-settings>p{margin:0;color:var(--ui-text-muted);line-height:1.55}.switch-row{display:flex;align-items:center;gap:.55rem;font-weight:700}.switch-row input{width:1.1rem;height:1.1rem;accent-color:var(--ui-primary)}.note-field{display:grid;gap:.45rem;font-weight:700}.note-field input{min-height:3rem;padding:0 var(--ui-space-3);border:1px solid var(--ui-border);border-radius:var(--ui-radius-md);background:var(--ui-surface);color:var(--ui-text);font:inherit}.note-field input:disabled{opacity:.55}.actions{display:flex;align-items:center;justify-content:flex-end;gap:var(--ui-space-3)}.notice{margin-right:auto;color:var(--ui-success)}.notice--error{color:var(--ui-danger)}.history{display:grid;gap:var(--ui-space-2);padding-top:var(--ui-space-3);border-top:1px solid var(--ui-border)}.history article{display:flex;align-items:center;gap:var(--ui-space-3);padding:.7rem;border-radius:var(--ui-radius-md);background:var(--ui-surface-muted)}.history .icon{font-size:1.35rem}.history article div{display:grid;gap:.15rem}.history small{color:var(--ui-text-subtle)}@media(max-width:680px){.support-settings header,.actions{align-items:stretch;flex-direction:column}.actions .ui-button{width:100%}.notice{margin-right:0}}
</style>
