<template>
	<Teleport to="body">
		<div v-if="open" class="space-modal" role="dialog" aria-modal="true" aria-labelledby="create-space-title">
			<button class="space-modal__backdrop" type="button" aria-label="Закрыть" @click="close" />
			<form class="space-modal__panel" @submit.prevent="submit">
				<header class="space-modal__header">
					<div>
						<span class="space-modal__eyebrow">Новое место в PubChat</span>
						<h2 id="create-space-title">Создать пространство</h2>
					</div>
					<button class="icon-button" type="button" aria-label="Закрыть" @click="close">
						<i class="fas fa-xmark" aria-hidden="true"></i>
					</button>
				</header>

				<div class="space-modal__body">
					<label class="field field--wide">
						<span>Название</span>
						<input v-model.trim="form.name" maxlength="80" required placeholder="Например, Кино после полуночи" />
						<small>От 3 до 80 символов. Название можно изменить позже.</small>
					</label>

					<label class="field field--wide">
						<span>О чём это место</span>
						<textarea v-model.trim="form.description" maxlength="500" rows="4" placeholder="Коротко опишите атмосферу, тему и для кого это пространство." />
					</label>

					<label class="field">
						<span>Формат</span>
						<select v-model="form.purpose">
							<option value="community">Сообщество</option>
							<option value="conversation">Разговоры</option>
							<option value="meet_people">Новые знакомства</option>
							<option value="games">Игры и активности</option>
							<option value="local">Локальное место</option>
						</select>
					</label>

					<label class="field">
						<span>Видимость</span>
						<select v-model="form.visibility">
							<option value="public">Публичное</option>
							<option value="unlisted">По ссылке</option>
							<option value="private">Закрытое</option>
						</select>
					</label>

					<label class="field">
						<span>Как присоединяются</span>
						<select v-model="form.join_policy">
							<option value="open">Сразу входят</option>
							<option value="request">По заявке</option>
							<option value="invite">По приглашению</option>
						</select>
					</label>

					<label class="field">
						<span>Лимит участников</span>
						<input v-model.number="form.member_limit" type="number" min="2" max="5000" />
					</label>

					<label class="field">
						<span>Страна</span>
						<input v-model.trim="form.country" maxlength="100" placeholder="Необязательно" />
					</label>

					<label class="field">
						<span>Регион / город</span>
						<input v-model.trim="form.region" maxlength="100" placeholder="Необязательно" />
					</label>

					<label class="field field--wide">
						<span>Теги</span>
						<input v-model="tagsText" maxlength="240" placeholder="кино, музыка, вильнюс" />
						<small>До 8 тегов, через запятую.</small>
					</label>

					<div v-if="errorMessage" class="form-error" role="alert">
						<i class="fas fa-circle-exclamation" aria-hidden="true"></i>
						<span>{{ errorMessage }}</span>
					</div>
				</div>

				<footer class="space-modal__footer">
					<button type="button" class="ui-button ui-button--ghost" :disabled="submitting" @click="close">Отмена</button>
					<button type="submit" class="ui-button" :disabled="!canSubmit || submitting">
						<span v-if="!submitting">Создать пространство</span>
						<span v-else>Создаём…</span>
					</button>
				</footer>
			</form>
		</div>
	</Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';

import SpacesService from '@/API/SpacesService';

const props = defineProps({
	open: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'created']);

const initialForm = () => ({
	name: '',
	description: '',
	purpose: 'community',
	visibility: 'public',
	join_policy: 'open',
	member_limit: 250,
	country: '',
	region: '',
});

const form = reactive(initialForm());
const tagsText = ref('');
const submitting = ref(false);
const errorMessage = ref('');

const canSubmit = computed(() => form.name.trim().length >= 3 && form.member_limit >= 2 && form.member_limit <= 5000);

const reset = () => {
	Object.assign(form, initialForm());
	tagsText.value = '';
	errorMessage.value = '';
};

const close = () => {
	if (submitting.value) return;
	emit('close');
};

const parsedTags = () => [...new Set(
	tagsText.value
		.split(',')
		.map((tag) => tag.trim())
		.filter(Boolean)
		.map((tag) => tag.slice(0, 40)),
)].slice(0, 8);

const submit = async () => {
	if (!canSubmit.value || submitting.value) return;
	submitting.value = true;
	errorMessage.value = '';
	try {
		const response = await SpacesService.create({
			...form,
			description: form.description || null,
			country: form.country || null,
			region: form.region || null,
			tags: parsedTags(),
		});
		emit('created', response.data.space);
		reset();
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		errorMessage.value = type === 'invalid_space_policy'
			? 'Для закрытого пространства выберите вход по заявке или приглашению.'
			: 'Не удалось создать пространство. Проверьте поля и попробуйте ещё раз.';
	} finally {
		submitting.value = false;
	}
};

watch(() => form.visibility, (visibility) => {
	if (visibility === 'private' && form.join_policy === 'open') form.join_policy = 'request';
});

watch(() => props.open, (open) => {
	if (open) errorMessage.value = '';
});
</script>

<style scoped>
.space-modal { position: fixed; inset: 0; z-index: 1400; display: grid; place-items: center; padding: var(--ui-space-4); }
.space-modal__backdrop { position: absolute; inset: 0; border: 0; background: rgba(15, 23, 42, 0.54); backdrop-filter: blur(4px); }
.space-modal__panel { position: relative; width: min(100%, 44rem); max-height: calc(100dvh - 2rem); display: flex; flex-direction: column; overflow: hidden; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface-raised); box-shadow: var(--ui-shadow-lg); }
.space-modal__header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--ui-space-4); padding: var(--ui-space-5); border-bottom: 1px solid var(--ui-border); }
.space-modal__eyebrow { display: block; margin-bottom: .25rem; color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.space-modal h2 { margin: 0; font-size: var(--ui-text-xl); }
.icon-button { width: 2.5rem; height: 2.5rem; display: grid; place-items: center; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text-muted); cursor: pointer; }
.space-modal__body { min-height: 0; overflow-y: auto; display: grid; grid-template-columns: 1fr 1fr; gap: var(--ui-space-4); padding: var(--ui-space-5); }
.field { min-width: 0; display: grid; gap: var(--ui-space-2); }
.field--wide { grid-column: 1 / -1; }
.field > span { color: var(--ui-text); font-size: var(--ui-text-sm); font-weight: 700; }
.field small { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }
.field input, .field textarea, .field select { width: 100%; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text); padding: .72rem .8rem; font: inherit; outline: none; }
.field input:focus, .field textarea:focus, .field select:focus { border-color: var(--ui-primary); box-shadow: 0 0 0 3px var(--ui-primary-soft); }
.field textarea { resize: vertical; min-height: 6rem; }
.form-error { grid-column: 1 / -1; display: flex; gap: var(--ui-space-2); padding: var(--ui-space-3); border-radius: var(--ui-radius-md); background: var(--ui-danger-soft); color: var(--ui-danger); font-size: var(--ui-text-sm); }
.space-modal__footer { display: flex; justify-content: flex-end; gap: var(--ui-space-2); padding: var(--ui-space-4) var(--ui-space-5); border-top: 1px solid var(--ui-border); background: var(--ui-surface-soft); }
.ui-button--ghost { background: transparent; color: var(--ui-text-muted); border: 1px solid var(--ui-border); }
@media (max-width: 640px) {
	.space-modal { padding: 0; align-items: end; }
	.space-modal__panel { max-height: 94dvh; border-radius: var(--ui-radius-xl) var(--ui-radius-xl) 0 0; }
	.space-modal__body { grid-template-columns: 1fr; padding: var(--ui-space-4); }
	.field--wide { grid-column: auto; }
	.space-modal__header, .space-modal__footer { padding-inline: var(--ui-space-4); }
	.space-modal__footer { position: sticky; bottom: 0; }
}
</style>
