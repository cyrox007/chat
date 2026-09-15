<template>
	<section class="space-support">
		<header class="support-head">
			<div><span class="eyebrow">Поддержка пространства</span><h2>Спасибо за атмосферу</h2></div>
			<button v-if="canGift" class="ui-button ui-button--ghost" type="button" @click="showPicker = !showPicker">{{ showPicker ? 'Закрыть' : 'Поддержать' }}</button>
		</header>

		<p class="support-copy">{{ settings.note || 'Бесплатные cosmetic gifts — знак благодарности сообществу, а не покупка влияния.' }}</p>

		<div v-if="items.length" class="gift-shelf">
			<span v-for="item in items" :key="item.gift.code" class="gift-chip"><span aria-hidden="true">{{ item.gift.icon }}</span><strong>{{ item.gift.name }}</strong><small>× {{ item.count }}</small></span>
		</div>
		<p v-else class="empty-copy">Пока без gifts. Это никак не влияет на видимость или ценность пространства.</p>

		<form v-if="showPicker && canGift" class="gift-picker" @submit.prevent="sendGift">
			<div class="gift-grid">
				<button v-for="gift in catalog" :key="gift.code" type="button" class="gift-option" :class="{ active: selectedGift === gift.code }" @click="selectedGift = gift.code">
					<span>{{ gift.icon }}</span><strong>{{ gift.name }}</strong><small>{{ gift.description }}</small>
				</button>
			</div>
			<label>Сообщение<textarea v-model.trim="message" maxlength="280" rows="2" placeholder="Необязательно"></textarea></label>
			<div class="actions"><small>Gift не даёт роли, приоритета или права на модерацию.</small><button class="ui-button" type="submit" :disabled="sending || !selectedGift">{{ sending ? 'Отправляем…' : 'Отправить' }}</button></div>
		</form>

		<div v-if="canManage" class="manager-panel">
			<label class="switch-row"><input v-model="settings.enabled" type="checkbox" /><span>{{ settings.enabled ? 'Получение gifts включено' : 'Получение gifts выключено' }}</span></label>
			<label>Пояснение<input v-model.trim="settings.note" maxlength="280" :disabled="!settings.enabled" placeholder="Например: Спасибо, что поддерживаете наши встречи" /></label>
			<button class="ui-button ui-button--secondary" type="button" :disabled="savingSettings" @click="saveSettings">{{ savingSettings ? 'Сохраняем…' : 'Сохранить настройки' }}</button>
			<div v-if="history.length" class="history">
				<strong>Последние полученные</strong>
				<article v-for="entry in history" :key="entry.uid"><span>{{ entry.gift.icon }}</span><div><strong>{{ entry.gift.name }}</strong><small>{{ entry.sender_label || 'Persona PubChat' }}<template v-if="entry.message"> · {{ entry.message }}</template></small></div></article>
			</div>
		</div>
		<p v-if="notice" :class="['notice', `notice--${notice.type}`]" role="status">{{ notice.message }}</p>
	</section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import SupportService from '@/API/SupportService';

const props = defineProps({
	spaceUid: { type: String, required: true },
	canManage: { type: Boolean, default: false },
	isActiveMember: { type: Boolean, default: false },
	isOwner: { type: Boolean, default: false },
});

const settings = reactive({ enabled: false, note: '' });
const items = ref([]);
const catalog = ref([]);
const history = ref([]);
const showPicker = ref(false);
const selectedGift = ref('');
const message = ref('');
const sending = ref(false);
const savingSettings = ref(false);
const notice = ref(null);
const canGift = computed(() => props.isActiveMember && !props.isOwner && settings.enabled);

const load = async () => {
	if (!props.spaceUid) return;
	try {
		const [shelfResponse, catalogResponse] = await Promise.all([
			SupportService.spaceShelf(props.spaceUid),
			SupportService.catalog('space'),
		]);
		Object.assign(settings, { enabled: Boolean(shelfResponse.data.settings?.enabled), note: shelfResponse.data.settings?.note || '' });
		items.value = shelfResponse.data.items || [];
		catalog.value = catalogResponse.data.gifts || [];
		selectedGift.value ||= catalog.value[0]?.code || '';
		if (props.canManage) {
			const historyResponse = await SupportService.spaceReceived(props.spaceUid, { limit: 8 });
			history.value = historyResponse.data.items || [];
		}
	} catch { notice.value = { type: 'error', message: 'Не удалось загрузить поддержку пространства.' }; }
};

const saveSettings = async () => {
	savingSettings.value = true; notice.value = null;
	try {
		const response = await SupportService.updateSpaceSettings(props.spaceUid, { enabled: settings.enabled, note: settings.enabled ? settings.note || null : null });
		Object.assign(settings, { enabled: Boolean(response.data.support?.enabled), note: response.data.support?.note || '' });
		notice.value = { type: 'success', message: 'Настройки поддержки сохранены.' };
	} catch { notice.value = { type: 'error', message: 'Не удалось сохранить настройки.' }; }
	finally { savingSettings.value = false; }
};

const sendGift = async () => {
	sending.value = true; notice.value = null;
	try {
		await SupportService.giftSpace(props.spaceUid, { gift_code: selectedGift.value, message: message.value || null });
		message.value = ''; showPicker.value = false; notice.value = { type: 'success', message: 'Знак поддержки отправлен пространству.' }; await load();
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		notice.value = { type: 'error', message: type === 'gift_daily_limit_reached' ? 'На сегодня достаточно — попробуйте позже.' : 'Не удалось отправить поддержку.' };
	} finally { sending.value = false; }
};

onMounted(load);
watch(() => props.spaceUid, load);
</script>

<style scoped>
.space-support{display:grid;gap:var(--ui-space-4);padding:var(--ui-space-5);border:1px solid var(--ui-border);border-radius:var(--ui-radius-xl);background:var(--ui-surface)}.support-head{display:flex;align-items:center;justify-content:space-between;gap:var(--ui-space-3)}.support-head h2{margin:.2rem 0 0}.eyebrow{color:var(--ui-primary);font-size:var(--ui-text-xs);font-weight:800;text-transform:uppercase;letter-spacing:.08em}.support-copy,.empty-copy{margin:0;color:var(--ui-text-muted)}.gift-shelf{display:flex;gap:var(--ui-space-2);flex-wrap:wrap}.gift-chip{display:inline-flex;align-items:center;gap:.45rem;padding:.55rem .75rem;border:1px solid var(--ui-border);border-radius:999px;background:var(--ui-surface-muted)}.gift-chip small{color:var(--ui-text-subtle)}.gift-picker,.manager-panel{display:grid;gap:var(--ui-space-3);padding-top:var(--ui-space-3);border-top:1px solid var(--ui-border)}.gift-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--ui-space-2)}.gift-option{display:grid;gap:.2rem;min-height:6rem;padding:var(--ui-space-3);border:1px solid var(--ui-border);border-radius:var(--ui-radius-lg);background:var(--ui-surface-muted);color:var(--ui-text);text-align:left}.gift-option span{font-size:1.35rem}.gift-option small,.actions small{color:var(--ui-text-subtle)}.gift-option.active{border-color:var(--ui-primary);box-shadow:0 0 0 2px var(--ui-primary-soft)}.gift-picker label,.manager-panel>label:not(.switch-row){display:grid;gap:.4rem;font-weight:700}.gift-picker textarea,.manager-panel input{padding:.7rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-md);background:var(--ui-surface);color:var(--ui-text);font:inherit}.actions{display:flex;align-items:center;justify-content:space-between;gap:var(--ui-space-3)}.switch-row{display:flex;align-items:center;gap:.55rem;font-weight:700}.switch-row input{accent-color:var(--ui-primary)}.history{display:grid;gap:var(--ui-space-2)}.history article{display:flex;gap:var(--ui-space-3);align-items:center;padding:.7rem;border-radius:var(--ui-radius-md);background:var(--ui-surface-muted)}.history article div{display:grid;gap:.15rem}.history small{color:var(--ui-text-subtle)}.notice{margin:0;color:var(--ui-success)}.notice--error{color:var(--ui-danger)}@media(max-width:680px){.support-head,.actions{align-items:stretch;flex-direction:column}.gift-grid{grid-template-columns:1fr 1fr}.support-head .ui-button,.actions .ui-button{width:100%}}
</style>
