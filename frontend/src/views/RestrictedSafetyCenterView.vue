<template>
	<main class="restricted-shell">
		<section class="restricted-card">
			<div class="icon"><i class="fas fa-shield-halved"></i></div>
			<div>
				<span class="eyebrow">Trust & Safety</span>
				<h1>Доступ к PubChat ограничен</h1>
				<p>Основные функции временно недоступны. Здесь остаются только сведения об ограничении, апелляция и выход из аккаунта.</p>
			</div>
		</section>

		<section v-if="notice" class="notice" :class="`notice--${notice.type}`">{{ notice.message }}</section>
		<section v-if="loading" class="state">Загружаем решение…</section>

		<template v-else>
			<section v-if="accessRestriction" class="decision-card">
				<header>
					<div><span class="eyebrow">Platform restriction</span><h2>Полное ограничение доступа</h2></div>
					<span class="status">Активно</span>
				</header>
				<p>{{ accessRestriction.public_explanation }}</p>
				<dl>
					<div><dt>Начало</dt><dd>{{ formatDate(accessRestriction.starts_at) }}</dd></div>
					<div><dt>Срок</dt><dd>{{ accessRestriction.expires_at ? formatDate(accessRestriction.expires_at) : 'Без установленного срока' }}</dd></div>
				</dl>

				<form v-if="!appealForRestriction" class="appeal-form" @submit.prevent="submitAppeal">
					<label>Апелляция
						<textarea v-model.trim="appealBody" rows="5" maxlength="4000" placeholder="Опишите, почему решение следует пересмотреть" required></textarea>
					</label>
					<button class="ui-button" type="submit" :disabled="submitting || appealBody.length < 10">{{ submitting ? 'Отправляем…' : 'Отправить апелляцию' }}</button>
				</form>
				<div v-else class="appeal-status">
					<strong>Апелляция: {{ appealStatusLabel(appealForRestriction.status) }}</strong>
					<p>{{ appealForRestriction.body }}</p>
					<p v-if="appealForRestriction.resolution"><strong>Решение:</strong> {{ appealForRestriction.resolution }}</p>
				</div>
			</section>

			<section v-else class="state state--success">
				<strong>Активного ограничения доступа больше нет.</strong>
				<span>Можно вернуться в PubChat.</span>
				<button class="ui-button" type="button" @click="returnToApp">Вернуться</button>
			</section>

			<section class="history-card" v-if="otherRestrictions.length || appeals.length">
				<h2>История</h2>
				<article v-for="item in otherRestrictions" :key="item.uid">
					<strong>{{ capabilityLabel(item.capability) }}</strong>
					<span>{{ item.public_explanation }}</span>
					<small>{{ restrictionStatusLabel(item.status) }} · {{ item.expires_at ? formatDate(item.expires_at) : 'без срока' }}</small>
				</article>
			</section>
		</template>

		<footer>
			<button class="logout" type="button" @click="logout">Выйти из аккаунта</button>
		</footer>
	</main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';

import ModerationService from '@/API/ModerationService';

const store = useStore();
const router = useRouter();
const loading = ref(true);
const restrictions = ref([]);
const appeals = ref([]);
const appealBody = ref('');
const submitting = ref(false);
const notice = ref(null);

const accessRestriction = computed(() => restrictions.value.find((item) => item.capability === 'account.access' && item.status === 'active') || null);
const otherRestrictions = computed(() => restrictions.value.filter((item) => item.uid !== accessRestriction.value?.uid));
const appealForRestriction = computed(() => appeals.value.find((item) => item.restriction_uid === accessRestriction.value?.uid) || null);

const load = async () => {
	loading.value = true;
	try {
		const identity = await store.dispatch('syncIdentity');
		if (!identity.access_restriction) {
			store.commit('setAccessRestriction', null);
			await router.replace({ name: 'safety' });
			return;
		}
		const [restrictionResponse, appealResponse] = await Promise.all([
			ModerationService.myRestrictions({ include_inactive: true, limit: 100 }),
			ModerationService.myRestrictionAppeals({ limit: 100 }),
		]);
		restrictions.value = restrictionResponse.data.restrictions || [];
		appeals.value = appealResponse.data.appeals || [];
	} catch (error) {
		console.error(error);
		notice.value = { type: 'error', message: 'Не удалось загрузить сведения об ограничении.' };
	} finally {
		loading.value = false;
	}
};

const submitAppeal = async () => {
	if (!accessRestriction.value) return;
	submitting.value = true;
	try {
		await ModerationService.appealRestriction(accessRestriction.value.uid, appealBody.value);
		appealBody.value = '';
		const response = await ModerationService.myRestrictionAppeals({ limit: 100 });
		appeals.value = response.data.appeals || [];
		notice.value = { type: 'success', message: 'Апелляция отправлена на независимый пересмотр.' };
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		notice.value = {
			type: 'error',
			message: type === 'platform_restriction_appeal_exists' ? 'Апелляция на это ограничение уже подана.' : 'Не удалось отправить апелляцию.',
		};
	} finally {
		submitting.value = false;
	}
};

const returnToApp = async () => {
	store.commit('setAccessRestriction', null);
	await router.replace({ name: 'chats' });
};

const logout = async () => {
	await store.dispatch('logout');
	await router.replace({ name: 'login' });
};

const capabilityLabel = (value) => ({
	'account.access': 'Доступ к платформе',
	'messenger.send': 'Отправка личных сообщений',
	'space.chat.send': 'Сообщения в пространствах',
	'media.upload': 'Загрузка медиа',
	'space.create': 'Создание пространств',
	'space.join': 'Вступление в пространства',
	'invitation.send': 'Отправка приглашений',
	'profile.edit': 'Изменение профиля',
	'discovery.publish': 'Появление в discovery',
}[value] || value);
const restrictionStatusLabel = (value) => ({ active: 'активно', expired: 'завершено', revoked: 'снято' }[value] || value);
const appealStatusLabel = (value) => ({ pending: 'на рассмотрении', upheld: 'решение оставлено', overturned: 'решение отменено' }[value] || value);
const formatDate = (value) => value ? new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '';

onMounted(load);
</script>

<style scoped>
.restricted-shell{max-width:760px;margin:0 auto;display:grid;gap:var(--ui-space-5);padding:var(--ui-space-6) var(--ui-space-4) var(--ui-space-8)}.restricted-card,.decision-card,.history-card,.state{border:1px solid var(--ui-border);border-radius:var(--ui-radius-xl);background:var(--ui-surface);padding:var(--ui-space-5)}.restricted-card{display:grid;grid-template-columns:auto 1fr;gap:var(--ui-space-4);align-items:start}.icon{width:3.4rem;height:3.4rem;display:grid;place-items:center;border-radius:var(--ui-radius-lg);background:var(--ui-danger-soft);color:var(--ui-danger);font-size:1.35rem}.eyebrow{color:var(--ui-primary);font-size:var(--ui-text-xs);font-weight:800;text-transform:uppercase;letter-spacing:.08em}h1,h2{margin:.3rem 0 .6rem}p{color:var(--ui-text-muted);line-height:1.55}.decision-card header{display:flex;justify-content:space-between;gap:var(--ui-space-3)}.status{align-self:start;padding:.25rem .55rem;border-radius:var(--ui-radius-pill);background:var(--ui-danger-soft);color:var(--ui-danger);font-size:var(--ui-text-xs);font-weight:800}dl{display:grid;grid-template-columns:1fr 1fr;gap:var(--ui-space-3);margin:var(--ui-space-4) 0}dl div{padding:var(--ui-space-3);border-radius:var(--ui-radius-md);background:var(--ui-surface-muted)}dt{font-size:var(--ui-text-xs);color:var(--ui-text-subtle)}dd{margin:.3rem 0 0;font-weight:700}.appeal-form{display:grid;gap:var(--ui-space-3);margin-top:var(--ui-space-4)}.appeal-form label{display:grid;gap:.4rem;font-weight:700}.appeal-form textarea{width:100%;padding:var(--ui-space-3);border:1px solid var(--ui-border);border-radius:var(--ui-radius-md);background:var(--ui-bg);color:var(--ui-text);font:inherit;resize:vertical}.appeal-status{margin-top:var(--ui-space-4);padding:var(--ui-space-4);border-radius:var(--ui-radius-lg);background:var(--ui-primary-soft)}.history-card{display:grid;gap:var(--ui-space-3)}.history-card article{display:grid;gap:.25rem;padding-top:var(--ui-space-3);border-top:1px solid var(--ui-border)}.history-card article span,.history-card article small{color:var(--ui-text-muted)}.notice{padding:var(--ui-space-3) var(--ui-space-4);border-radius:var(--ui-radius-lg);background:var(--ui-success-soft);color:var(--ui-success)}.notice--error{background:var(--ui-danger-soft);color:var(--ui-danger)}.state{display:grid;gap:var(--ui-space-2);text-align:center;color:var(--ui-text-muted)}.state--success strong{color:var(--ui-text)}footer{display:flex;justify-content:center}.logout{border:0;background:transparent;color:var(--ui-text-muted);text-decoration:underline;cursor:pointer}@media(max-width:560px){.restricted-card{grid-template-columns:1fr}.decision-card header{display:grid}dl{grid-template-columns:1fr}.appeal-form .ui-button{width:100%}}
</style>
