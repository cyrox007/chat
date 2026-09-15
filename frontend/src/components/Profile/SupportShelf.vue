<template>
	<section class="support-card" v-if="!loading && visible">
		<header class="support-head">
			<div><span class="eyebrow">Поддержка</span><h2>Тёплые знаки внимания</h2></div>
			<button v-if="canGift" class="ui-button ui-button--ghost" type="button" @click="showPicker = !showPicker">
				{{ showPicker ? 'Закрыть' : 'Поддержать' }}
			</button>
		</header>
		<p class="support-note">{{ supportNote }}</p>
		<div v-if="items.length" class="gift-shelf" aria-label="Полученные знаки поддержки">
			<span v-for="item in items" :key="item.gift.code" class="gift-chip" :title="item.gift.description || item.gift.name">
				<span aria-hidden="true">{{ item.gift.icon }}</span><strong>{{ item.gift.name }}</strong><small>× {{ item.count }}</small>
			</span>
		</div>
		<p v-else class="empty-copy">Здесь пока тихо. Gifts не являются рейтингом и не влияют на возможности Persona.</p>

		<form v-if="showPicker && canGift" class="gift-picker" @submit.prevent="sendGift">
			<div class="gift-grid">
				<button v-for="gift in catalog" :key="gift.code" type="button" class="gift-option" :class="{ active: selectedGift === gift.code }" @click="selectedGift = gift.code">
					<span aria-hidden="true">{{ gift.icon }}</span><strong>{{ gift.name }}</strong><small>{{ gift.description }}</small>
				</button>
			</div>
			<label>Короткое сообщение<textarea v-model.trim="message" maxlength="280" rows="2" placeholder="Необязательно"></textarea></label>
			<div class="picker-footer">
				<small>Это бесплатный жест. Он не даёт прав, рейтинга или преимуществ.</small>
				<button class="ui-button" type="submit" :disabled="sending || !selectedGift">{{ sending ? 'Отправляем…' : 'Отправить' }}</button>
			</div>
		</form>
		<p v-if="notice" :class="['notice', `notice--${notice.type}`]" role="status">{{ notice.message }}</p>
	</section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import SupportService from '@/API/SupportService';

const props = defineProps({
	accountUid: { type: String, default: '' },
	personaUid: { type: String, default: '' },
	isSelf: { type: Boolean, default: false },
});

const loading = ref(true);
const resolvedPersonaUid = ref(props.personaUid || '');
const settings = ref({ enabled: false, note: null });
const items = ref([]);
const catalog = ref([]);
const showPicker = ref(false);
const selectedGift = ref('');
const message = ref('');
const sending = ref(false);
const notice = ref(null);

const visible = computed(() => props.isSelf || settings.value.enabled || items.value.length > 0);
const canGift = computed(() => Boolean(resolvedPersonaUid.value && !props.isSelf && settings.value.enabled));
const supportNote = computed(() => settings.value.note || 'Gifts — спокойный способ сказать спасибо без покупки статуса.');

const load = async () => {
	if (!props.personaUid && !props.accountUid) return;
	loading.value = true;
	try {
		const response = props.personaUid
			? await SupportService.personaShelf(props.personaUid)
			: await SupportService.accountShelf(props.accountUid);
		resolvedPersonaUid.value = props.personaUid || response.data.persona_uid || '';
		settings.value = response.data.settings || { enabled: false, note: null };
		items.value = response.data.items || [];
		if (canGift.value) {
			const catalogResponse = await SupportService.catalog('persona');
			catalog.value = catalogResponse.data.gifts || [];
			selectedGift.value ||= catalog.value[0]?.code || '';
		}
	} catch {
		settings.value = { enabled: false, note: null };
		items.value = [];
	} finally { loading.value = false; }
};

const sendGift = async () => {
	if (!selectedGift.value || !resolvedPersonaUid.value) return;
	sending.value = true; notice.value = null;
	try {
		await SupportService.giftPersona(resolvedPersonaUid.value, { gift_code: selectedGift.value, message: message.value || null });
		message.value = ''; showPicker.value = false;
		notice.value = { type: 'success', message: 'Знак поддержки отправлен.' };
		await load();
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		notice.value = { type: 'error', message: type === 'gift_daily_limit_reached' ? 'На сегодня достаточно — попробуйте снова позже.' : 'Не удалось отправить поддержку.' };
	} finally { sending.value = false; }
};

onMounted(load);
watch(() => [props.accountUid, props.personaUid], load);
</script>

<style scoped>
.support-card{display:grid;gap:var(--ui-space-4);padding:var(--ui-space-5);border:1px solid var(--ui-border);border-radius:var(--ui-radius-xl);background:var(--ui-surface)}.support-head{display:flex;align-items:center;justify-content:space-between;gap:var(--ui-space-4)}.support-head h2{margin:.2rem 0 0;font-size:var(--ui-text-xl)}.eyebrow{color:var(--ui-primary);font-size:var(--ui-text-xs);font-weight:800;letter-spacing:.08em;text-transform:uppercase}.support-note,.empty-copy{margin:0;color:var(--ui-text-muted);line-height:1.55}.gift-shelf{display:flex;flex-wrap:wrap;gap:var(--ui-space-2)}.gift-chip{display:inline-flex;align-items:center;gap:.45rem;padding:.55rem .75rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-pill);background:var(--ui-surface-muted)}.gift-chip small{color:var(--ui-text-subtle)}.gift-picker{display:grid;gap:var(--ui-space-3);padding-top:var(--ui-space-3);border-top:1px solid var(--ui-border)}.gift-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--ui-space-2)}.gift-option{min-height:6rem;display:grid;align-content:center;gap:.2rem;padding:var(--ui-space-3);border:1px solid var(--ui-border);border-radius:var(--ui-radius-lg);background:var(--ui-surface-muted);color:var(--ui-text);text-align:left;cursor:pointer}.gift-option>span{font-size:1.35rem}.gift-option small{color:var(--ui-text-subtle)}.gift-option.active{border-color:var(--ui-primary);box-shadow:0 0 0 2px var(--ui-primary-soft)}.gift-picker label{display:grid;gap:.4rem;font-weight:700}.gift-picker textarea{padding:.7rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-md);background:var(--ui-surface);color:var(--ui-text);font:inherit;resize:vertical}.picker-footer{display:flex;align-items:center;justify-content:space-between;gap:var(--ui-space-3)}.picker-footer small{color:var(--ui-text-subtle)}.notice{margin:0;color:var(--ui-success)}.notice--error{color:var(--ui-danger)}@media(max-width:680px){.support-head,.picker-footer{align-items:stretch;flex-direction:column}.gift-grid{grid-template-columns:1fr 1fr}.support-head .ui-button,.picker-footer .ui-button{width:100%}}
</style>
