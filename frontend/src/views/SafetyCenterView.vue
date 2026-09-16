<template>
	<main class="safety-shell">
		<section class="safety-hero">
			<div>
				<span class="eyebrow">Безопасность</span>
				<h1>Решения должны быть понятными и оспоримыми</h1>
				<p>Здесь можно сообщить о проблеме внутри пространства, увидеть свои жалобы и решения модерации, а также подать апелляцию.</p>
			</div>
			<div class="principle"><i class="fas fa-scale-balanced"></i><span>Жалобы не публикуются участникам. Решение и его причина видны затронутому пользователю.</span></div>
		</section>

		<section v-if="notice" class="notice" :class="`notice--${notice.type}`" role="status">{{ notice.message }}</section>

		<section class="report-card">
			<header><div><span>Новая жалоба</span><strong>Сообщить о проблеме в пространстве</strong></div></header>
			<form @submit.prevent="submitReport">
				<label>Пространство
					<select v-model="reportDraft.space_uid" required @change="loadMembers">
						<option value="">Выберите пространство</option>
						<option v-for="space in memberSpaces" :key="space.uid" :value="space.uid">{{ space.name }}</option>
					</select>
				</label>
				<label>Участник
					<select v-model="reportDraft.target_account_uid" required :disabled="!reportDraft.space_uid || membersLoading">
						<option value="">{{ membersLoading ? 'Загружаем участников…' : 'Выберите участника' }}</option>
						<option v-for="member in reportableMembers" :key="member.account_uid" :value="member.account_uid">{{ member.persona?.display_name || member.persona?.handle || member.account_uid }}</option>
					</select>
				</label>
				<label>Причина
					<select v-model="reportDraft.category" required>
						<option value="spam">Спам</option><option value="harassment">Оскорбления / преследование</option><option value="sexual">Сексуальный контент</option><option value="violence">Угрозы / насилие</option><option value="privacy">Нарушение приватности</option><option value="other">Другое</option>
					</select>
				</label>
				<label class="wide">Комментарий<textarea v-model.trim="reportDraft.description" maxlength="2000" rows="3" placeholder="Опишите, что произошло. Не публикуйте лишние персональные данные."></textarea></label>
				<div class="wide form-actions"><span>Команда выбранного пространства увидит жалобу в своей moderation queue.</span><button class="ui-button" type="submit" :disabled="submittingReport || !reportDraft.target_account_uid">{{ submittingReport ? 'Отправляем…' : 'Отправить жалобу' }}</button></div>
			</form>
		</section>

		<nav class="safety-tabs">
			<button v-for="tab in tabs" :key="tab.value" type="button" :class="{ active: activeTab === tab.value }" @click="activeTab = tab.value">{{ tab.label }}<span>{{ tab.count }}</span></button>
		</nav>

		<section v-if="loading" class="state-block"><i class="fas fa-circle-notch fa-spin"></i><strong>Загружаем историю…</strong></section>

		<section v-else-if="activeTab === 'reports'" class="record-list">
			<article v-for="report in reports" :key="report.uid" class="record-card">
				<div class="record-icon"><i class="fas fa-flag"></i></div>
				<div><div class="record-title"><strong>{{ categoryLabel(report.category) }}</strong><span :class="`status status--${report.status}`">{{ reportStatusLabel(report.status) }}</span></div><p>{{ report.description || 'Без дополнительного комментария.' }}</p><small>{{ report.target?.display_name || report.target?.handle || 'Участник' }} · {{ formatDate(report.created_at) }}</small></div>
			</article>
			<div v-if="!reports.length" class="state-block state-block--compact"><i class="fas fa-flag"></i><strong>Жалоб пока нет</strong><span>Это хорошо. Если понадобится помощь, новая жалоба останется видна здесь.</span></div>
		</section>

		<section v-else-if="activeTab === 'actions'" class="record-list">
			<article v-for="action in actions" :key="action.uid" class="record-card record-card--action">
				<div class="record-icon"><i :class="action.action_type === 'restrict' ? 'fas fa-shield-halved' : 'fas fa-triangle-exclamation'"></i></div>
				<div><div class="record-title"><strong>{{ actionLabel(action.action_type) }}</strong><span :class="`status status--${action.status}`">{{ actionStatusLabel(action.status) }}</span></div><p>{{ action.reason }}</p><small>{{ action.expires_at ? `До ${formatDate(action.expires_at)}` : 'Без срока' }} · назначено {{ formatDate(action.starts_at) }}</small>
					<button v-if="canAppeal(action)" type="button" class="appeal-link" @click="openAppeal(action.uid)"><i class="fas fa-scale-balanced"></i>Подать апелляцию</button>
					<div v-if="appealActionUid === action.uid" class="appeal-form"><textarea v-model.trim="appealBody" rows="3" maxlength="4000" placeholder="Объясните, почему решение стоит пересмотреть"></textarea><div><button type="button" @click="appealActionUid = null">Отмена</button><button class="ui-button" type="button" :disabled="appealBody.length < 10 || appealSubmitting" @click="submitAppeal(action)">{{ appealSubmitting ? 'Отправляем…' : 'Отправить' }}</button></div></div>
				</div>
			</article>
			<div v-if="!actions.length" class="state-block state-block--compact"><i class="fas fa-shield"></i><strong>Решений модерации нет</strong><span>Здесь появятся только действия, которые относятся лично к вашему аккаунту.</span></div>
		</section>

		<section v-else-if="activeTab === 'restrictions'" class="record-list">
			<article v-for="restriction in restrictions" :key="restriction.uid" class="record-card record-card--action">
				<div class="record-icon"><i class="fas fa-user-shield"></i></div>
				<div>
					<div class="record-title"><strong>{{ capabilityLabel(restriction.capability) }}</strong><span :class="`status status--${restriction.status}`">{{ restrictionStatusLabel(restriction.status) }}</span></div>
					<p>{{ restriction.public_explanation }}</p>
					<small>{{ restriction.scope_type === 'space' ? 'Только выбранное пространство' : 'Вся платформа' }} · {{ restriction.expires_at ? `до ${formatDate(restriction.expires_at)}` : 'без установленного срока' }}</small>
				</div>
			</article>
			<div v-if="!restrictions.length" class="state-block state-block--compact"><i class="fas fa-user-shield"></i><strong>Ограничений возможностей нет</strong><span>Здесь будут видны platform-level ограничения вашего Account, их причина и срок.</span></div>
		</section>

		<section v-else class="record-list">
			<article v-for="appeal in appeals" :key="appeal.uid" class="record-card">
				<div class="record-icon"><i class="fas fa-scale-balanced"></i></div>
				<div><div class="record-title"><strong>Апелляция на: {{ actionLabel(appeal.action_type) }}</strong><span :class="`status status--${appeal.status}`">{{ appealStatusLabel(appeal.status) }}</span></div><p>{{ appeal.body }}</p><div v-if="appeal.resolution" class="resolution"><strong>Решение по апелляции</strong><span>{{ appeal.resolution }}</span></div><small>{{ formatDate(appeal.created_at) }}</small></div>
			</article>
			<div v-if="!appeals.length" class="state-block state-block--compact"><i class="fas fa-scale-balanced"></i><strong>Апелляций нет</strong><span>Апелляция доступна из карточки конкретного moderation-action.</span></div>
		</section>
	</main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useStore } from 'vuex';

import ModerationService from '@/API/ModerationService';
import SpacesService from '@/API/SpacesService';

const store = useStore();
const loading = ref(true);
const reports = ref([]);
const actions = ref([]);
const restrictions = ref([]);
const appeals = ref([]);
const memberSpaces = ref([]);
const members = ref([]);
const membersLoading = ref(false);
const submittingReport = ref(false);
const activeTab = ref('reports');
const notice = ref(null);
const appealActionUid = ref(null);
const appealBody = ref('');
const appealSubmitting = ref(false);
const reportDraft = reactive({ space_uid: '', target_account_uid: '', category: 'harassment', description: '' });

const currentUserUid = computed(() => store.getters.getUser?.uid);
const reportableMembers = computed(() => members.value.filter((item) => item.account_uid !== currentUserUid.value));
const tabs = computed(() => [
	{ value: 'reports', label: 'Мои жалобы', count: reports.value.length },
	{ value: 'actions', label: 'Решения Space', count: actions.value.length },
	{ value: 'restrictions', label: 'Ограничения', count: restrictions.value.length },
	{ value: 'appeals', label: 'Апелляции', count: appeals.value.length },
]);
const appealByAction = computed(() => new Set(appeals.value.map((item) => item.action_uid)));

const flash = (message, type = 'success') => { notice.value = { message, type }; window.setTimeout(() => { if (notice.value?.message === message) notice.value = null; }, 3500); };

const loadSafety = async () => {
	loading.value = true;
	try {
		const [reportsResponse, actionsResponse, restrictionsResponse, appealsResponse, spacesResponse] = await Promise.all([
			ModerationService.myReports({ limit: 100 }),
			ModerationService.myActions({ limit: 100 }),
			ModerationService.myRestrictions({ include_inactive: true, limit: 100 }),
			ModerationService.myAppeals({ limit: 100 }),
			SpacesService.list({ limit: 50 }),
		]);
		reports.value = reportsResponse.data.reports || [];
		actions.value = actionsResponse.data.actions || [];
		restrictions.value = restrictionsResponse.data.restrictions || [];
		appeals.value = appealsResponse.data.appeals || [];
		memberSpaces.value = (spacesResponse.data.spaces || []).filter((space) => space.viewer_membership?.status === 'active' || space.viewer_membership?.role === 'owner');
	} catch (error) { console.error(error); flash('Не удалось загрузить центр безопасности.', 'error'); } finally { loading.value = false; }
};

const loadMembers = async () => {
	members.value = []; reportDraft.target_account_uid = '';
	if (!reportDraft.space_uid) return;
	membersLoading.value = true;
	try { const response = await SpacesService.members(reportDraft.space_uid, { status: 'active', limit: 100 }); members.value = response.data.members || []; }
	catch (error) { flash('Не удалось загрузить участников пространства.', 'error'); }
	finally { membersLoading.value = false; }
};

const submitReport = async () => {
	submittingReport.value = true;
	try {
		await ModerationService.createReport(reportDraft.space_uid, { target_account_uid: reportDraft.target_account_uid, category: reportDraft.category, description: reportDraft.description || null });
		Object.assign(reportDraft, { target_account_uid: '', category: 'harassment', description: '' });
		const response = await ModerationService.myReports({ limit: 100 }); reports.value = response.data.reports || [];
		activeTab.value = 'reports'; flash('Жалоба отправлена команде пространства.');
	} catch (error) { flash('Не удалось отправить жалобу.', 'error'); } finally { submittingReport.value = false; }
};

const canAppeal = (action) => action.status !== 'revoked' && !appealByAction.value.has(action.uid);
const openAppeal = (actionUid) => { appealActionUid.value = actionUid; appealBody.value = ''; };
const submitAppeal = async (action) => {
	appealSubmitting.value = true;
	try {
		await ModerationService.appeal(action.uid, appealBody.value);
		const response = await ModerationService.myAppeals({ limit: 100 }); appeals.value = response.data.appeals || [];
		appealActionUid.value = null; appealBody.value = ''; activeTab.value = 'appeals'; flash('Апелляция отправлена на пересмотр.');
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		flash(type === 'moderation_appeal_exists' ? 'Апелляция на это решение уже существует.' : 'Не удалось отправить апелляцию.', 'error');
	} finally { appealSubmitting.value = false; }
};

const categoryLabel = (value) => ({ spam: 'Спам', harassment: 'Оскорбления / преследование', sexual: 'Сексуальный контент', violence: 'Угрозы / насилие', privacy: 'Нарушение приватности', other: 'Другое' }[value] || value);
const reportStatusLabel = (value) => ({ open: 'Открыта', reviewing: 'На рассмотрении', resolved: 'Решена', dismissed: 'Закрыта без действия' }[value] || value);
const actionLabel = (value) => ({ warning: 'Предупреждение', restrict: 'Ограничение доступа' }[value] || value);
const actionStatusLabel = (value) => ({ active: 'Активно', expired: 'Завершено', revoked: 'Отменено' }[value] || value);
const restrictionStatusLabel = (value) => ({ active: 'Активно', expired: 'Завершено', revoked: 'Снято' }[value] || value);
const capabilityLabel = (value) => ({ 'messenger.send': 'Отправка личных сообщений', 'space.chat.send': 'Сообщения в пространствах', 'media.upload': 'Загрузка медиа', 'space.create': 'Создание пространств', 'space.join': 'Вступление в пространства', 'invitation.send': 'Отправка приглашений', 'profile.edit': 'Изменение профиля', 'discovery.publish': 'Публикация в discovery', 'account.access': 'Доступ к Account' }[value] || value);
const appealStatusLabel = (value) => ({ pending: 'На рассмотрении', upheld: 'Решение оставлено', overturned: 'Решение отменено' }[value] || value);
const formatDate = (value) => new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));

onMounted(loadSafety);
</script>

<style scoped>
.safety-shell { display: grid; gap: var(--ui-space-5); padding-bottom: var(--ui-space-8); }.safety-hero { display: grid; grid-template-columns: minmax(0, 1fr) minmax(15rem, 22rem); gap: var(--ui-space-6); padding: clamp(1.4rem, 4vw, 2.5rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: linear-gradient(135deg, var(--ui-surface) 0%, var(--ui-success-soft) 180%); }.eyebrow { color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }.safety-hero h1 { margin: .35rem 0 0; font-size: clamp(1.8rem, 4vw, 2.8rem); line-height: 1.05; letter-spacing: -.035em; }.safety-hero p { margin: var(--ui-space-3) 0 0; color: var(--ui-text-muted); line-height: 1.6; }.principle { align-self: center; display: flex; gap: var(--ui-space-3); padding: var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface); color: var(--ui-text-muted); font-size: var(--ui-text-sm); line-height: 1.5; }.principle i { color: var(--ui-primary); margin-top: .15rem; }
.notice { padding: var(--ui-space-3) var(--ui-space-4); border-radius: var(--ui-radius-lg); background: var(--ui-success-soft); color: var(--ui-success); }.notice--error { background: var(--ui-danger-soft); color: var(--ui-danger); }.report-card { padding: var(--ui-space-5); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); }.report-card header div { display: grid; margin-bottom: var(--ui-space-4); }.report-card header span { color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; text-transform: uppercase; }.report-card form { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--ui-space-3); }.report-card label { display: grid; gap: .35rem; color: var(--ui-text-muted); font-size: var(--ui-text-xs); font-weight: 700; }.report-card select, .report-card textarea { width: 100%; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-bg); color: var(--ui-text); font: inherit; }.report-card select { min-height: 2.75rem; padding: 0 var(--ui-space-3); }.report-card textarea { padding: var(--ui-space-3); resize: vertical; }.wide { grid-column: 1 / -1; }.form-actions { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; gap: var(--ui-space-3); }.form-actions span { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }
.safety-tabs { display: flex; gap: var(--ui-space-2); overflow-x: auto; }.safety-tabs button { min-height: 2.7rem; display: flex; align-items: center; gap: var(--ui-space-2); padding: 0 var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface); color: var(--ui-text-muted); font: inherit; font-weight: 700; cursor: pointer; }.safety-tabs button.active { background: var(--ui-primary-soft); color: var(--ui-primary); }.safety-tabs button span { min-width: 1.3rem; padding: .1rem .35rem; border-radius: var(--ui-radius-pill); background: var(--ui-surface-muted); font-size: .68rem; }.record-list { display: grid; gap: var(--ui-space-3); }.record-card { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--ui-space-3); padding: var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface); }.record-icon { width: 2.7rem; height: 2.7rem; display: grid; place-items: center; border-radius: var(--ui-radius-lg); background: var(--ui-primary-soft); color: var(--ui-primary); }.record-title { display: flex; align-items: center; justify-content: space-between; gap: var(--ui-space-3); }.record-card p { margin: .45rem 0; color: var(--ui-text-muted); line-height: 1.5; white-space: pre-wrap; }.record-card small { color: var(--ui-text-subtle); }.status { flex: 0 0 auto; padding: .2rem .5rem; border-radius: var(--ui-radius-pill); background: var(--ui-surface-muted); color: var(--ui-text-muted); font-size: .65rem; font-weight: 800; }.status--active, .status--open, .status--pending { background: var(--ui-warning-soft); color: var(--ui-warning); }.status--resolved, .status--overturned, .status--revoked { background: var(--ui-success-soft); color: var(--ui-success); }.status--dismissed, .status--expired, .status--upheld { background: var(--ui-surface-muted); color: var(--ui-text-muted); }.appeal-link { display: inline-flex; align-items: center; gap: .4rem; margin-top: var(--ui-space-3); padding: 0; border: 0; background: transparent; color: var(--ui-primary); font: inherit; font-size: var(--ui-text-sm); font-weight: 700; cursor: pointer; }.appeal-form { display: grid; gap: var(--ui-space-2); margin-top: var(--ui-space-3); padding: var(--ui-space-3); border-radius: var(--ui-radius-lg); background: var(--ui-surface-muted); }.appeal-form textarea { width: 100%; padding: var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text); font: inherit; }.appeal-form > div { display: flex; justify-content: flex-end; gap: var(--ui-space-2); }.appeal-form button { min-height: 2.35rem; padding: 0 var(--ui-space-3); border: 0; border-radius: var(--ui-radius-md); cursor: pointer; }.resolution { display: grid; gap: .25rem; margin: var(--ui-space-3) 0; padding: var(--ui-space-3); border-left: 3px solid var(--ui-primary); background: var(--ui-primary-soft); }.resolution span { color: var(--ui-text-muted); font-size: var(--ui-text-sm); }.state-block { min-height: 16rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); text-align: center; color: var(--ui-text-muted); }.state-block--compact { min-height: 11rem; padding: var(--ui-space-5); border: 1px dashed var(--ui-border); border-radius: var(--ui-radius-xl); }.state-block i { color: var(--ui-primary); font-size: 2rem; }.state-block strong { color: var(--ui-text); }
@media (max-width: 800px) { .safety-hero { grid-template-columns: 1fr; }.report-card form { grid-template-columns: 1fr; }.wide { grid-column: auto; }.form-actions { grid-column: auto; align-items: stretch; flex-direction: column; }.form-actions .ui-button { width: 100%; }.record-title { align-items: flex-start; flex-direction: column; } }
</style>