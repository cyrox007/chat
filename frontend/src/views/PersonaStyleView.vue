<template>
	<main class="studio-shell">
		<section class="studio-hero">
			<div>
				<span class="eyebrow">Стиль образа</span>
				<h1>Внешний вид — это самовыражение, не статус</h1>
				<p>Настройте настроение Persona. Эти параметры не влияют на доверие, права или видимость в discovery.</p>
			</div>
			<div class="preview" :class="[`preview--${draft.background_preset}`, `preview-accent--${draft.accent_preset}`]">
				<span class="preview-avatar" :class="`frame--${draft.avatar_frame_preset}`">P</span>
				<strong>{{ draft.status_line || 'Свободно общаюсь в PubChat' }}</strong>
				<small>Косметический слой Persona</small>
			</div>
		</section>

		<section v-if="loading" class="state-card" role="status">Загружаем стиль…</section>
		<form v-else class="studio-card" @submit.prevent="save">
			<div class="field-group">
				<label>Акцент</label>
				<div class="option-grid">
					<button v-for="item in accents" :key="item.value" type="button" class="option" :class="{ active: draft.accent_preset === item.value }" @click="draft.accent_preset = item.value">
						<span class="swatch" :class="`swatch--${item.value}`"></span><strong>{{ item.label }}</strong>
					</button>
				</div>
			</div>

			<div class="field-group">
				<label>Фон профиля</label>
				<div class="option-grid">
					<button v-for="item in backgrounds" :key="item.value" type="button" class="option" :class="{ active: draft.background_preset === item.value }" @click="draft.background_preset = item.value">
						<strong>{{ item.label }}</strong><small>{{ item.hint }}</small>
					</button>
				</div>
			</div>

			<div class="field-group">
				<label>Рамка аватара</label>
				<div class="option-grid option-grid--compact">
					<button v-for="item in frames" :key="item.value" type="button" class="option" :class="{ active: draft.avatar_frame_preset === item.value }" @click="draft.avatar_frame_preset = item.value">{{ item.label }}</button>
				</div>
			</div>

			<label class="text-field">Строка настроения
				<input v-model.trim="draft.status_line" maxlength="120" placeholder="Например: Сегодня хочется лёгких разговоров" />
				<small>Короткая подпись к вашему образу. Не заменяет social intent.</small>
			</label>

			<div class="form-footer">
				<span v-if="notice" :class="['notice', `notice--${notice.type}`]">{{ notice.message }}</span>
				<button class="ui-button" type="submit" :disabled="saving">{{ saving ? 'Сохраняем…' : 'Сохранить стиль' }}</button>
			</div>
		</form>

		<SupportSettings />
	</main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';

import EngagementService from '@/API/EngagementService';
import SupportSettings from '@/components/Profile/SupportSettings.vue';

const loading = ref(true);
const saving = ref(false);
const notice = ref(null);
const draft = reactive({ accent_preset: 'plum', background_preset: 'soft', avatar_frame_preset: 'none', status_line: '' });

const accents = [
	{ value: 'plum', label: 'Слива' }, { value: 'berry', label: 'Ягода' }, { value: 'forest', label: 'Лес' }, { value: 'ocean', label: 'Океан' }, { value: 'sand', label: 'Песок' },
];
const backgrounds = [
	{ value: 'soft', label: 'Мягкий', hint: 'Спокойная нейтральная поверхность' },
	{ value: 'paper', label: 'Бумага', hint: 'Тёплый светлый фон' },
	{ value: 'mist', label: 'Туман', hint: 'Холодный приглушённый фон' },
	{ value: 'night', label: 'Ночь', hint: 'Глубокая тёмная поверхность' },
];
const frames = [
	{ value: 'none', label: 'Без рамки' }, { value: 'soft', label: 'Мягкая' }, { value: 'double', label: 'Двойная' }, { value: 'badge', label: 'Значок' },
];

const apply = (appearance = {}) => Object.assign(draft, {
	accent_preset: appearance.accent_preset || 'plum',
	background_preset: appearance.background_preset || 'soft',
	avatar_frame_preset: appearance.avatar_frame_preset || 'none',
	status_line: appearance.status_line || '',
});

const load = async () => {
	loading.value = true;
	try { const response = await EngagementService.myPersonaAppearance(); apply(response.data.appearance); }
	catch (error) { notice.value = { type: 'error', message: 'Не удалось загрузить настройки образа.' }; }
	finally { loading.value = false; }
};

const save = async () => {
	saving.value = true; notice.value = null;
	try {
		const response = await EngagementService.updateMyPersonaAppearance({ ...draft, status_line: draft.status_line || null });
		apply(response.data.appearance); notice.value = { type: 'success', message: 'Стиль Persona сохранён.' };
	} catch (error) { notice.value = { type: 'error', message: 'Не удалось сохранить стиль.' }; }
	finally { saving.value = false; }
};

onMounted(load);
</script>

<style scoped>
.studio-shell { display: grid; gap: var(--ui-space-5); padding-bottom: var(--ui-space-8); }.studio-hero { display: grid; grid-template-columns: minmax(0,1.2fr) minmax(16rem,.8fr); gap: var(--ui-space-6); padding: clamp(1.4rem,4vw,2.6rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); }.eyebrow { color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }.studio-hero h1 { margin: .4rem 0 0; font-size: clamp(1.8rem,4vw,2.8rem); line-height: 1.05; }.studio-hero p { max-width: 42rem; color: var(--ui-text-muted); line-height: 1.6; }.preview { min-height: 12rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); padding: var(--ui-space-5); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); text-align: center; }.preview--paper { background: color-mix(in srgb, var(--ui-warning-soft) 45%, var(--ui-surface)); }.preview--mist { background: color-mix(in srgb, var(--ui-info-soft) 45%, var(--ui-surface)); }.preview--night { background: color-mix(in srgb, var(--ui-text) 88%, var(--ui-surface)); color: var(--ui-surface); }.preview-avatar { width: 4.6rem; height: 4.6rem; display: grid; place-items: center; border-radius: 50%; background: var(--ui-primary-soft); color: var(--ui-primary); font-weight: 900; font-size: 1.4rem; }.frame--soft { box-shadow: 0 0 0 .35rem color-mix(in srgb, var(--ui-primary) 18%, transparent); }.frame--double { box-shadow: 0 0 0 .16rem var(--ui-surface), 0 0 0 .38rem var(--ui-primary); }.frame--badge { border-radius: 1.25rem; transform: rotate(-2deg); }.studio-card { display: grid; gap: var(--ui-space-6); padding: var(--ui-space-5); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); }.field-group { display: grid; gap: var(--ui-space-3); }.field-group > label,.text-field { font-weight: 750; }.option-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: var(--ui-space-2); }.option-grid--compact { grid-template-columns: repeat(4,minmax(0,1fr)); }.option { min-height: 4.7rem; display: grid; align-content: center; gap: .25rem; padding: var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface-muted); color: var(--ui-text); text-align: left; cursor: pointer; }.option.active { border-color: var(--ui-primary); box-shadow: 0 0 0 2px var(--ui-primary-soft); }.option small,.text-field small { color: var(--ui-text-subtle); font-weight: 500; }.swatch { width: 1.3rem; height: 1.3rem; border-radius: 50%; background: var(--ui-primary); }.swatch--berry { background: #a24569; }.swatch--forest { background: #50715d; }.swatch--ocean { background: #47748c; }.swatch--sand { background: #a77b52; }.text-field { display: grid; gap: var(--ui-space-2); }.text-field input { min-height: 3rem; padding: 0 var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text); font: inherit; }.form-footer { display: flex; justify-content: flex-end; align-items: center; gap: var(--ui-space-3); }.notice { margin-right: auto; color: var(--ui-success); }.notice--error { color: var(--ui-danger); }.state-card { padding: var(--ui-space-6); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); color: var(--ui-text-muted); }
@media (max-width: 760px) { .studio-hero { grid-template-columns: 1fr; }.option-grid,.option-grid--compact { grid-template-columns: repeat(2,minmax(0,1fr)); }.form-footer { align-items: stretch; flex-direction: column; }.form-footer .ui-button { width: 100%; }.notice { margin-right: 0; } }
</style>