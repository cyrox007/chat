<template>
	<div class="reminder-control" :class="{ active: Boolean(reminder) }">
		<i class="fas fa-bell" aria-hidden="true"></i>
		<select v-model.number="leadMinutes" :disabled="saving" aria-label="Когда напомнить">
			<option :value="15">за 15 минут</option>
			<option :value="60">за час</option>
			<option :value="1440">за день</option>
		</select>
		<button v-if="!reminder" type="button" :disabled="saving" @click="enable">{{ saving ? 'Сохраняем…' : 'Напомнить' }}</button>
		<template v-else>
			<button type="button" class="save" :disabled="saving || leadMinutes === reminder.lead_minutes" @click="enable">{{ saving ? '…' : 'Изменить' }}</button>
			<button type="button" class="clear" :disabled="saving" aria-label="Отключить напоминание" @click="disable"><i class="fas fa-xmark"></i></button>
		</template>
	</div>
	<span v-if="errorMessage" class="reminder-error" role="status">{{ errorMessage }}</span>
</template>

<script setup>
import { ref, watch } from 'vue';

import NotificationService from '@/API/NotificationService';

const props = defineProps({
	activityUid: { type: String, required: true },
	reminder: { type: Object, default: null },
});
const emit = defineEmits(['changed']);

const leadMinutes = ref(props.reminder?.lead_minutes || 60);
const saving = ref(false);
const errorMessage = ref('');

watch(() => props.reminder, (value) => {
	leadMinutes.value = value?.lead_minutes || 60;
});

const enable = async () => {
	saving.value = true;
	errorMessage.value = '';
	try {
		const response = await NotificationService.setReminder(props.activityUid, leadMinutes.value);
		emit('changed', response.data.reminder);
	} catch (error) {
		errorMessage.value = error.response?.status === 403
			? 'Напоминания доступны участникам пространства.'
			: 'Не удалось сохранить напоминание.';
	} finally {
		saving.value = false;
	}
};

const disable = async () => {
	saving.value = true;
	errorMessage.value = '';
	try {
		await NotificationService.clearReminder(props.activityUid);
		emit('changed', null);
	} catch {
		errorMessage.value = 'Не удалось отключить напоминание.';
	} finally {
		saving.value = false;
	}
};
</script>

<style scoped>
.reminder-control { display: inline-flex; align-items: center; gap: .35rem; min-height: 2.35rem; padding: .2rem .25rem .2rem .65rem; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface); color: var(--ui-text-muted); }.reminder-control.active { border-color: color-mix(in srgb,var(--ui-primary) 28%,var(--ui-border)); background: var(--ui-primary-soft); color: var(--ui-primary); }.reminder-control > i { font-size: .75rem; }.reminder-control select { min-width: 6.7rem; border: 0; outline: 0; background: transparent; color: inherit; font: inherit; font-size: var(--ui-text-xs); cursor: pointer; }.reminder-control button { min-height: 1.85rem; padding: 0 .65rem; border: 0; border-radius: var(--ui-radius-pill); background: var(--ui-primary); color: var(--ui-primary-contrast); font: inherit; font-size: var(--ui-text-xs); font-weight: 750; cursor: pointer; }.reminder-control .save:disabled { opacity: .45; }.reminder-control .clear { width: 1.85rem; padding: 0; background: transparent; color: var(--ui-primary); }.reminder-control button:disabled,.reminder-control select:disabled { cursor: not-allowed; opacity: .6; }.reminder-error { display: block; margin-top: .3rem; color: var(--ui-danger); font-size: var(--ui-text-xs); }
@media (max-width: 560px) { .reminder-control { width: 100%; }.reminder-control select { flex: 1; min-width: 0; } }
</style>
