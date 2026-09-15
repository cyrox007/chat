<template>
	<main class="moderation-shell">
		<header class="moderation-header">
			<div>
				<RouterLink class="back-link" :to="{ name: 'space-community', params: { uid: spaceUid } }"><i class="fas fa-arrow-left"></i>Центр пространства</RouterLink>
				<span class="eyebrow">Модерация</span>
				<h1>{{ space?.name || 'Пространство' }}</h1>
				<p>Жалобы, принятые решения и апелляции. Все действия scoped только этим пространством.</p>
			</div>
			<span v-if="space?.viewer_membership?.role" class="role-badge">{{ roleLabel(space.viewer_membership.role) }}</span>
		</header>

		<section v-if="notice" class="notice" :class="`notice--${notice.type}`" role="status">{{ notice.message }}</section>
		<section v-if="forbidden" class="state-block"><i class="fas fa-lock"></i><strong>Нужна роль управляющего</strong><span>Очередь модерации доступна создателю и модераторам этого пространства.</span></section>

		<template v-else>
			<nav class="moderation-tabs">
				<button v-for="tab in tabs" :key="tab.value" type="button" :class="{ active: activeTab === tab.value }" @click="activeTab = tab.value">{{ tab.label }}<span>{{ tab.count }}</span></button>
			</nav>

			<section v-if="loading" class="state-block"><i class="fas fa-circle-notch fa-spin"></i><strong>Загружаем очередь…</strong></section>

			<section v-else-if="activeTab === 'reports'" class="queue-list">
				<article v-for="report in reports" :key="report.uid" class="queue-card">
					<header class="queue-card__header"><div><strong>{{ categoryLabel(report.category) }}</strong><span>{{ report.reporter?.display_name || report.reporter?.handle || 'Участник' }} → {{ report.target?.display_name || report.target?.handle || 'Участник' }}</span></div><span :class="`status status--${report.status}`">{{ reportStatusLabel(report.status) }}</span></header>
					<p>{{ report.description || 'Без дополнительного комментария.' }}</p>
					<small>{{ formatDate(report.created_at) }}<template v-if="report.message_uid"> · сообщение {{ shortUid(report.message_uid) }}</template></small>
					<div v-if="report.status === 'open' || report.status === 'reviewing'" class="report-actions">
						<button v-if="report.status === 'open'" type="button" class="ui-button ui-button--ghost" @click="markReport(report, 'reviewing')">Взять в работу</button>
						<button type="button" class="ui-button ui-button--ghost" @click="markReport(report, 'dismissed')">Закрыть без действия</button>
						<button type="button" class="ui-button" @click="openAction(report)">Принять решение</button>
					</div>
					<form v-if="actionReportUid === report.uid" class="action-form" @submit.prevent="submitAction(report)">
						<label>Действие<select v-model="actionDraft.action_type"><option value="warning">Предупреждение</option><option value="restrict">Ограничить доступ</option></select></label>
						<label v-if="actionDraft.action_type === 'restrict'">Срок<select v-model="actionDraft.duration"><option value="60">1 час</option><option value="1440">1 день</option><option value="10080">7 дней</option><option value="43200">30 дней</option><option value="">Без срока</option></select></label>
						<label class="wide">Причина<textarea v-model.trim="actionDraft.reason" required minlength="3" maxlength="2000" rows="3" placeholder="Конкретно объясните, какое правило или граница были нарушены"></textarea></label>
						<div class="wide action-form__footer"><button type="button" @click="actionReportUid = null">Отмена</button><button class="ui-button" type="submit" :disabled="savingAction">{{ savingAction ? 'Сохраняем…' : 'Зафиксировать решение' }}</button></div>
					</form>
				</article>
				<div v-if="!reports.length" class="state-block state-block--compact"><i class="fas fa-inbox"></i><strong>Очередь пуста</strong><span>Новых жалоб для этого пространства нет.</span></div>
			</section>

			<section v-else-if="activeTab === 'actions'" class="queue-list">
				<article v-for="action in actions" :key="action.uid" class="queue-card">
					<header class="queue-card__header"><div><strong>{{ actionLabel(action.action_type) }} · {{ action.target?.display_name || action.target?.handle || 'Участник' }}</strong><span>Решение: {{ action.moderator?.display_name || action.moderator?.handle || 'Модератор' }}</span></div><span :class="`status status--${action.status}`">{{ actionStatusLabel(action.status) }}</span></header>
					<p>{{ action.reason }}</p><small>{{ formatDate(action.starts_at) }}<template v-if="action.expires_at"> · до {{ formatDate(action.expires_at) }}</template></small>
				</article>
				<div v-if="!actions.length" class="state-block state-block--compact"><i class="fas fa-scale-balanced"></i><strong>Решений пока нет</strong><span>Здесь появится журнал scoped moderation-actions.</span></div>
			</section>

			<section v-else class="queue-list">
				<article v-for="appeal in appeals" :key="appeal.uid" class="queue-card appeal-card">
					<header class="queue-card__header"><div><strong>{{ appeal.appellant?.display_name || appeal.appellant?.handle || 'Участник' }} просит пересмотреть {{ actionLabel(appeal.action_type).toLowerCase() }}</strong><span>Исходная причина: {{ appeal.reason }}</span></div><span class="status status--pending">На рассмотрении</span></header>
					<blockquote>{{ appeal.body }}</blockquote>
					<div v-if="appealUid === appeal.uid" class="appeal-resolution">
						<textarea v-model.trim="appealResolution" rows="3" maxlength="4000" placeholder="Объясните итог пересмотра"></textarea>
						<div><button type="button" @click="appealUid = null">Отмена</button><button type="button" class="ui-button ui-button--ghost" :disabled="appealResolution.length < 3 || resolvingAppeal" @click="resolveAppealItem(appeal, 'uphold')">Оставить решение</button><button type="button" class="ui-button" :disabled="appealResolution.length < 3 || resolvingAppeal" @click="resolveAppealItem(appeal, 'overturn')">Отменить решение</button></div>
					</div>
					<button v-else type="button" class="review-button" @click="openAppeal(appeal)"><i class="fas fa-scale-balanced"></i>Рассмотреть апелляцию</button>
				</article>
				<div v-if="!appeals.length" class="state-block state-block--compact"><i class="fas fa-scale-balanced"></i><strong>Апелляций нет</strong><span>Новые запросы на пересмотр появятся здесь.</span></div>
			</section>
		</template>
	</main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import ModerationService from '@/API/ModerationService';
import SpacesService from '@/API/SpacesService';

const route = useRoute();
const spaceUid = computed(() => String(route.params.uid || ''));
const space = ref(null);
const reports = ref([]);
const actions = ref([]);
const appeals = ref([]);
const loading = ref(true);
const forbidden = ref(false);
const activeTab = ref('reports');
const notice = ref(null);
const actionReportUid = ref(null);
const savingAction = ref(false);
const actionDraft = reactive({ action_type: 'warning', duration: '1440', reason: '' });
const appealUid = ref(null);
const appealResolution = ref('');
const resolvingAppeal = ref(false);

const tabs = computed(() => [
	{ value: 'reports', label: 'Жалобы', count: reports.value.filter((item) => ['open', 'reviewing'].includes(item.status)).length },
	{ value: 'actions', label: 'Решения', count: actions.value.length },
	{ value: 'appeals', label: 'Апелляции', count: appeals.value.length },
]);
const flash = (message, type = 'success') => { notice.value = { message, type }; window.setTimeout(() => { if (notice.value?.message === message) notice.value = null; }, 3500); };

const loadQueue = async () => {
	loading.value = true; forbidden.value = false;
	try {
		const spaceResponse = await SpacesService.get(spaceUid.value); space.value = spaceResponse.data.space;
		if (!space.value?.can_manage) { forbidden.value = true; return; }
		const [reportsResponse, actionsResponse, appealsResponse] = await Promise.all([
			ModerationService.reports(spaceUid.value, { limit: 100 }), ModerationService.actions(spaceUid.value, { limit: 100 }), ModerationService.appeals(spaceUid.value, { limit: 100 }),
		]);
		reports.value = reportsResponse.data.reports || []; actions.value = actionsResponse.data.actions || []; appeals.value = appealsResponse.data.appeals || [];
	} catch (error) {
		if (error.response?.status === 403) forbidden.value = true; else { console.error(error); flash('Не удалось загрузить очередь модерации.', 'error'); }
	} finally { loading.value = false; }
};

const markReport = async (report, status) => {
	try { const response = await ModerationService.updateReport(spaceUid.value, report.uid, status); report.status = response.data.report.status; flash(status === 'reviewing' ? 'Жалоба взята в работу.' : 'Жалоба закрыта без moderation-action.'); }
	catch (error) { flash('Не удалось изменить статус жалобы.', 'error'); }
};
const openAction = (report) => { actionReportUid.value = report.uid; Object.assign(actionDraft, { action_type: 'warning', duration: '1440', reason: '' }); };
const submitAction = async (report) => {
	if (!report.target?.account_uid) return;
	savingAction.value = true;
	try {
		const payload = { target_account_uid: report.target.account_uid, action_type: actionDraft.action_type, reason: actionDraft.reason, report_uid: report.uid, duration_minutes: actionDraft.action_type === 'restrict' && actionDraft.duration ? Number(actionDraft.duration) : null };
		await ModerationService.createAction(spaceUid.value, payload);
		actionReportUid.value = null;
		await loadQueue(); activeTab.value = 'actions'; flash('Решение зафиксировано и доступно пользователю.');
	} catch (error) { flash('Не удалось зафиксировать решение.', 'error'); } finally { savingAction.value = false; }
};

const openAppeal = (appeal) => { appealUid.value = appeal.uid; appealResolution.value = ''; };
const resolveAppealItem = async (appeal, decision) => {
	resolvingAppeal.value = true;
	try {
		await ModerationService.resolveAppeal(spaceUid.value, appeal.uid, { decision, resolution: appealResolution.value });
		appealUid.value = null; appealResolution.value = ''; await loadQueue(); activeTab.value = 'appeals'; flash(decision === 'overturn' ? 'Решение отменено, связанное ограничение снято.' : 'Решение оставлено в силе.');
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		flash(type === 'moderation_appeal_reviewer_conflict' ? 'Автор исходного решения не может сам рассматривать эту апелляцию.' : 'Не удалось завершить пересмотр.', 'error');
	} finally { resolvingAppeal.value = false; }
};

const roleLabel = (role) => ({ owner: 'Создатель', moderator: 'Модератор' }[role] || role);
const categoryLabel = (value) => ({ spam: 'Спам', harassment: 'Оскорбления / преследование', sexual: 'Сексуальный контент', violence: 'Угрозы / насилие', privacy: 'Нарушение приватности', other: 'Другое' }[value] || value);
const reportStatusLabel = (value) => ({ open: 'Открыта', reviewing: 'В работе', resolved: 'Решена', dismissed: 'Закрыта' }[value] || value);
const actionLabel = (value) => ({ warning: 'Предупреждение', restrict: 'Ограничение доступа' }[value] || value);
const actionStatusLabel = (value) => ({ active: 'Активно', expired: 'Завершено', revoked: 'Отменено' }[value] || value);
const formatDate = (value) => new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
const shortUid = (value) => `${String(value).slice(0, 8)}…`;

onMounted(loadQueue);
</script>

<style scoped>
.moderation-shell { display: grid; gap: var(--ui-space-5); padding-bottom: var(--ui-space-8); }.moderation-header { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--ui-space-5); padding: clamp(1.4rem, 4vw, 2.4rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: linear-gradient(135deg, var(--ui-surface) 0%, var(--ui-warning-soft) 180%); }.moderation-header > div { max-width: 44rem; }.back-link { display: inline-flex; align-items: center; gap: .4rem; margin-bottom: var(--ui-space-3); color: var(--ui-text-muted); text-decoration: none; font-size: var(--ui-text-sm); }.eyebrow { color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }.moderation-header h1 { margin: .3rem 0 0; font-size: clamp(1.8rem, 4vw, 2.7rem); }.moderation-header p { margin: var(--ui-space-2) 0 0; color: var(--ui-text-muted); line-height: 1.55; }.role-badge { padding: .4rem .7rem; border-radius: var(--ui-radius-pill); background: var(--ui-surface); color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; }.notice { padding: var(--ui-space-3) var(--ui-space-4); border-radius: var(--ui-radius-lg); background: var(--ui-success-soft); color: var(--ui-success); }.notice--error { background: var(--ui-danger-soft); color: var(--ui-danger); }
.moderation-tabs { display: flex; gap: var(--ui-space-2); overflow-x: auto; }.moderation-tabs button { min-height: 2.7rem; display: flex; align-items: center; gap: var(--ui-space-2); padding: 0 var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface); color: var(--ui-text-muted); font: inherit; font-weight: 700; cursor: pointer; }.moderation-tabs button.active { background: var(--ui-primary-soft); color: var(--ui-primary); }.moderation-tabs button span { min-width: 1.3rem; padding: .1rem .35rem; border-radius: var(--ui-radius-pill); background: var(--ui-surface-muted); font-size: .68rem; }.queue-list { display: grid; gap: var(--ui-space-3); }.queue-card { padding: var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface); }.queue-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--ui-space-3); }.queue-card__header > div { display: grid; gap: .25rem; }.queue-card__header span { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }.queue-card p { margin: var(--ui-space-3) 0; color: var(--ui-text-muted); white-space: pre-wrap; line-height: 1.5; }.queue-card small { color: var(--ui-text-subtle); }.status { flex: 0 0 auto; padding: .2rem .5rem; border-radius: var(--ui-radius-pill); background: var(--ui-surface-muted); color: var(--ui-text-muted) !important; font-size: .65rem !important; font-weight: 800; }.status--open, .status--active, .status--pending { background: var(--ui-warning-soft); color: var(--ui-warning) !important; }.status--reviewing { background: var(--ui-info-soft); color: var(--ui-info) !important; }.status--resolved, .status--revoked { background: var(--ui-success-soft); color: var(--ui-success) !important; }.report-actions { display: flex; flex-wrap: wrap; gap: var(--ui-space-2); margin-top: var(--ui-space-3); padding-top: var(--ui-space-3); border-top: 1px solid var(--ui-border); }.action-form { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--ui-space-3); margin-top: var(--ui-space-4); padding: var(--ui-space-4); border-radius: var(--ui-radius-lg); background: var(--ui-surface-muted); }.action-form label { display: grid; gap: .35rem; color: var(--ui-text-muted); font-size: var(--ui-text-xs); font-weight: 700; }.action-form select, .action-form textarea { width: 100%; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text); font: inherit; }.action-form select { min-height: 2.6rem; padding: 0 var(--ui-space-3); }.action-form textarea { padding: var(--ui-space-3); }.wide { grid-column: 1 / -1; }.action-form__footer { display: flex; justify-content: flex-end; gap: var(--ui-space-2); }.action-form__footer > button:first-child { border: 0; background: transparent; color: var(--ui-text-muted); cursor: pointer; }.appeal-card blockquote { margin: var(--ui-space-3) 0; padding: var(--ui-space-3) var(--ui-space-4); border-left: 3px solid var(--ui-primary); background: var(--ui-primary-soft); color: var(--ui-text); line-height: 1.5; }.review-button { display: inline-flex; align-items: center; gap: .4rem; margin-top: var(--ui-space-2); padding: 0; border: 0; background: transparent; color: var(--ui-primary); font: inherit; font-weight: 700; cursor: pointer; }.appeal-resolution { display: grid; gap: var(--ui-space-2); margin-top: var(--ui-space-3); }.appeal-resolution textarea { width: 100%; padding: var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-bg); color: var(--ui-text); font: inherit; }.appeal-resolution > div { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: var(--ui-space-2); }.appeal-resolution > div > button:first-child { border: 0; background: transparent; color: var(--ui-text-muted); cursor: pointer; }.state-block { min-height: 18rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); padding: var(--ui-space-5); text-align: center; color: var(--ui-text-muted); }.state-block--compact { min-height: 11rem; border: 1px dashed var(--ui-border); border-radius: var(--ui-radius-xl); }.state-block i { color: var(--ui-primary); font-size: 2rem; }.state-block strong { color: var(--ui-text); }
@media (max-width: 700px) { .moderation-header { align-items: stretch; flex-direction: column; }.queue-card__header { flex-direction: column; }.action-form { grid-template-columns: 1fr; }.wide { grid-column: auto; }.action-form__footer, .appeal-resolution > div { align-items: stretch; flex-direction: column; }.action-form__footer .ui-button, .appeal-resolution .ui-button { width: 100%; } }
</style>
