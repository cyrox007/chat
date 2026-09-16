<template>
	<main class="ts-shell">
		<header class="ts-hero">
			<div>
				<span class="eyebrow">Trust & Safety</span>
				<h1>Очередь жалоб платформы</h1>
				<p>Platform-level разбор отделён от модерации конкретного пространства. Evidence открывается только после claim и каждое открытие аудируется.</p>
			</div>
			<div class="hero-note"><i class="fas fa-shield-halved"></i><span>Смотрите только тот материал, который был пожалован. Эта очередь не даёт произвольного доступа к личной переписке.</span></div>
		</header>

		<section class="filters" aria-label="Фильтры очереди">
			<label>Статус<select v-model="filters.status" @change="loadQueue"><option value="">Активные</option><option value="triage">Новые</option><option value="in_review">В работе</option><option value="escalated">Эскалация</option></select></label>
			<label>Приоритет<select v-model="filters.priority" @change="loadQueue"><option value="">Любой</option><option value="high">Высокий</option><option value="normal">Обычный</option><option value="low">Низкий</option></select></label>
			<label>Назначение<select v-model="filters.assigned" @change="loadQueue"><option value="any">Все</option><option value="unassigned">Свободные</option><option value="mine">Мои</option></select></label>
			<button class="ui-button ui-button--ghost" type="button" :disabled="loading" @click="loadQueue"><i class="fas fa-rotate"></i> Обновить</button>
		</section>

		<section v-if="notice" class="notice" :class="`notice--${notice.type}`" role="status">{{ notice.message }}</section>

		<div class="workspace">
			<section class="queue-panel">
				<div v-if="loading" class="state">Загружаем очередь…</div>
				<div v-else-if="!reports.length" class="state"><strong>Очередь пуста</strong><span>По выбранным фильтрам активных жалоб нет.</span></div>
				<button v-for="report in reports" :key="report.uid" type="button" class="report-card" :class="{ active: selected?.uid === report.uid }" @click="selectReport(report)">
					<span class="priority" :class="`priority--${report.priority}`">{{ priorityLabel(report.priority) }}</span>
					<span class="report-copy"><strong>{{ categoryLabel(report.category) }}</strong><span>{{ sourceLabel(report.source_type) }} · {{ report.target?.display_name || report.target?.handle || 'Account' }}</span><small>{{ statusLabel(report.status) }} · {{ formatDate(report.created_at) }}</small></span>
					<i class="fas fa-chevron-right"></i>
				</button>
			</section>

			<section class="review-panel">
				<div v-if="!selected" class="state state--review"><i class="fas fa-shield"></i><strong>Выберите жалобу</strong><span>Evidence не загружается до того, как вы возьмёте жалобу в работу.</span></div>
				<template v-else>
					<header class="review-head">
						<div><span class="eyebrow">{{ sourceLabel(selected.source_type) }}</span><h2>{{ categoryLabel(selected.category) }}</h2><p>{{ selected.description || 'Без комментария пользователя.' }}</p></div>
						<span class="status-pill">{{ statusLabel(selected.status) }}</span>
					</header>

					<div class="review-actions">
						<button v-if="!selected.assigned_to_account_uid" class="ui-button" type="button" :disabled="busy" @click="claim">Взять в работу</button>
						<button v-else-if="ownsSelected && selected.status === 'in_review'" class="ui-button ui-button--ghost" type="button" :disabled="busy" @click="release">Освободить</button>
						<button v-if="ownsSelected" class="ui-button ui-button--ghost" type="button" :disabled="busy" @click="loadEvidence">Показать evidence</button>
					</div>

					<section v-if="evidence" class="evidence">
						<header><strong>Пожалованный объект</strong><span>{{ evidence.available ? 'Доступен' : 'Больше недоступен' }}</span></header>
						<template v-if="evidence.persona"><strong>{{ evidence.persona.display_name || evidence.persona.handle }}</strong><p>@{{ evidence.persona.handle }}</p><p>{{ evidence.persona.bio || 'Описание отсутствует.' }}</p></template>
						<template v-else-if="evidence.message"><div class="message-evidence"><small>{{ formatDate(evidence.message.created_at) }}</small><p>{{ evidence.message.content || `[${evidence.message.content_type}]` }}</p></div><small>{{ evidence.context_policy === 'reported_message_only' ? 'Показано только пожалованное сообщение, без истории диалога.' : '' }}</small></template>
					</section>

					<form v-if="ownsSelected && ['in_review', 'escalated'].includes(selected.status)" class="decision" @submit.prevent="decide">
						<h3>Решение по triage</h3>
						<div class="decision-grid">
							<label>Статус<select v-model="decision.status"><option value="resolved">Решено</option><option value="dismissed">Закрыть без действия</option><option value="escalated">Требуется platform action</option></select></label>
							<label>Код<select v-model="decision.resolution_code"><option value="handled">Обработано</option><option value="no_violation">Нарушение не подтверждено</option><option value="insufficient_context">Недостаточно контекста</option><option value="duplicate">Дубликат</option><option value="needs_platform_action">Нужно действие платформы</option><option value="other">Другое</option></select></label>
						</div>
						<label>Пояснение пользователю<textarea v-model.trim="decision.public_explanation" maxlength="1000" rows="3" required placeholder="Кратко и понятно: что произошло с жалобой. Это увидит отправитель."></textarea></label>
						<button class="ui-button" type="submit" :disabled="busy || decision.public_explanation.length < 3">Сохранить решение</button>
					</form>

					<section v-if="audit.length" class="audit"><h3>Аудит</h3><div v-for="event in audit" :key="event.uid" class="audit-row"><span>{{ auditLabel(event.event_type) }}</span><small>{{ formatDate(event.created_at) }}</small></div></section>
				</template>
			</section>
		</div>
	</main>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useStore } from 'vuex';

import ModerationService from '@/API/ModerationService';

const store = useStore();
const reports = ref([]);
const selected = ref(null);
const evidence = ref(null);
const audit = ref([]);
const loading = ref(true);
const busy = ref(false);
const notice = ref(null);
const filters = reactive({ status: '', priority: '', assigned: 'any' });
const decision = reactive({ status: 'resolved', resolution_code: 'handled', public_explanation: '' });

const currentAccountUid = computed(() => store.getters.getAccount?.uid || store.getters.getUser?.uid || null);
const ownsSelected = computed(() => Boolean(selected.value?.assigned_to_account_uid && selected.value.assigned_to_account_uid === currentAccountUid.value));

const flash = (message, type = 'success') => {
	notice.value = { message, type };
	window.setTimeout(() => { if (notice.value?.message === message) notice.value = null; }, 3500);
};

const queueParams = () => Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
const loadQueue = async () => {
	loading.value = true;
	try {
		const response = await ModerationService.trustSafetyQueue({ ...queueParams(), limit: 100 });
		reports.value = response.data.reports || [];
		if (selected.value) selected.value = reports.value.find((item) => item.uid === selected.value.uid) || null;
	} catch (error) {
		flash(error.response?.status === 403 ? 'Нет platform Trust & Safety permission.' : 'Не удалось загрузить очередь.', 'error');
	} finally { loading.value = false; }
};

const selectReport = (report) => { selected.value = report; evidence.value = null; audit.value = []; decision.public_explanation = ''; if (report.assigned_to_account_uid === currentAccountUid.value) loadAudit(); };
const replaceSelected = (report) => { selected.value = report; const index = reports.value.findIndex((item) => item.uid === report.uid); if (index >= 0) reports.value[index] = report; };

const claim = async () => {
	busy.value = true;
	try { const response = await ModerationService.claimTrustSafetyReport(selected.value.uid); replaceSelected(response.data.report); await loadAudit(); flash('Жалоба закреплена за вами.'); }
	catch (error) { flash(error.response?.data?.detail?.error_type === 'trust_safety_report_already_claimed' ? 'Жалобу уже взял другой модератор.' : 'Не удалось взять жалобу.', 'error'); await loadQueue(); }
	finally { busy.value = false; }
};
const release = async () => {
	busy.value = true;
	try { const response = await ModerationService.releaseTrustSafetyReport(selected.value.uid); replaceSelected(response.data.report); evidence.value = null; audit.value = []; flash('Жалоба возвращена в общую очередь.'); }
	catch { flash('Не удалось освободить жалобу.', 'error'); }
	finally { busy.value = false; }
};
const loadEvidence = async () => {
	busy.value = true;
	try { const response = await ModerationService.trustSafetyEvidence(selected.value.uid); evidence.value = response.data.evidence; await loadAudit(); }
	catch { flash('Evidence доступен только владельцу claim.', 'error'); }
	finally { busy.value = false; }
};
const loadAudit = async () => {
	if (!selected.value) return;
	try { const response = await ModerationService.trustSafetyAudit(selected.value.uid); audit.value = response.data.events || []; } catch { audit.value = []; }
};
const decide = async () => {
	busy.value = true;
	try { const response = await ModerationService.decideTrustSafetyReport(selected.value.uid, { ...decision }); replaceSelected(response.data.report); await loadAudit(); flash(decision.status === 'escalated' ? 'Жалоба эскалирована.' : 'Решение сохранено.'); await loadQueue(); }
	catch (error) { const type = error.response?.data?.detail?.error_type; flash(type === 'trust_safety_claim_required' ? 'Claim больше не принадлежит вам.' : 'Не удалось сохранить решение.', 'error'); }
	finally { busy.value = false; }
};

watch(() => decision.status, (value) => { if (value === 'escalated') decision.resolution_code = 'needs_platform_action'; else if (decision.resolution_code === 'needs_platform_action') decision.resolution_code = value === 'dismissed' ? 'no_violation' : 'handled'; });

const priorityLabel = (value) => ({ high: 'Высокий', normal: 'Обычный', low: 'Низкий' }[value] || value);
const statusLabel = (value) => ({ triage: 'Новая', in_review: 'В работе', escalated: 'Эскалация', resolved: 'Решено', dismissed: 'Закрыто' }[value] || value);
const sourceLabel = (value) => ({ persona: 'Профиль', messenger_message: 'Личное сообщение', space_message: 'Сообщение пространства' }[value] || value);
const categoryLabel = (value) => ({ spam: 'Спам', harassment: 'Преследование', sexual: 'Сексуальный контент', violence: 'Угрозы / насилие', privacy: 'Приватность', impersonation: 'Выдача себя за другого', fraud: 'Мошенничество', hate: 'Ненависть / травля группы', self_harm: 'Риск самоповреждения', minor_safety: 'Безопасность несовершеннолетних', other: 'Другое' }[value] || value);
const auditLabel = (value) => ({ report_created: 'Жалоба создана', duplicate_submission: 'Повторная отправка', report_claimed: 'Взято в работу', report_released: 'Возвращено в очередь', evidence_viewed: 'Evidence просмотрен', report_decided: 'Решение сохранено' }[value] || value);
const formatDate = (value) => value ? new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '';

onMounted(loadQueue);
</script>

<style scoped>
.ts-shell{display:grid;gap:var(--ui-space-5);padding-bottom:var(--ui-space-8)}.ts-hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(15rem,22rem);gap:var(--ui-space-5);padding:clamp(1.25rem,4vw,2.3rem);border:1px solid var(--ui-border);border-radius:var(--ui-radius-xl);background:linear-gradient(135deg,var(--ui-surface),var(--ui-primary-soft))}.eyebrow{color:var(--ui-primary);font-size:var(--ui-text-xs);font-weight:800;letter-spacing:.08em;text-transform:uppercase}.ts-hero h1,.review-head h2{margin:.3rem 0 0}.ts-hero p,.review-head p{color:var(--ui-text-muted);line-height:1.55}.hero-note{align-self:center;display:flex;gap:.7rem;padding:1rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-lg);background:var(--ui-surface);color:var(--ui-text-muted);line-height:1.45}.hero-note i{color:var(--ui-primary)}.filters{display:flex;gap:.75rem;align-items:end;flex-wrap:wrap}.filters label,.decision label{display:grid;gap:.35rem;color:var(--ui-text-muted);font-size:var(--ui-text-sm)}select,textarea{border:1px solid var(--ui-border);border-radius:var(--ui-radius-md);background:var(--ui-surface);color:var(--ui-text);padding:.65rem .75rem}.workspace{display:grid;grid-template-columns:minmax(17rem,25rem) minmax(0,1fr);gap:var(--ui-space-4);align-items:start}.queue-panel,.review-panel{display:grid;gap:.65rem}.review-panel{min-height:24rem;padding:var(--ui-space-4);border:1px solid var(--ui-border);border-radius:var(--ui-radius-xl);background:var(--ui-surface)}.report-card{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:.7rem;width:100%;padding:.8rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-lg);background:var(--ui-surface);color:var(--ui-text);text-align:left;cursor:pointer}.report-card.active{border-color:var(--ui-primary);box-shadow:0 0 0 2px var(--ui-primary-soft)}.report-copy{min-width:0;display:grid;gap:.15rem}.report-copy span,.report-copy small{color:var(--ui-text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.priority{padding:.2rem .45rem;border-radius:var(--ui-radius-pill);font-size:.65rem;font-weight:800}.priority--high{background:var(--ui-danger-soft);color:var(--ui-danger)}.priority--normal{background:var(--ui-primary-soft);color:var(--ui-primary)}.priority--low{background:var(--ui-surface-muted);color:var(--ui-text-muted)}.review-head{display:flex;justify-content:space-between;gap:1rem}.review-head>div{min-width:0}.status-pill{align-self:start;padding:.3rem .6rem;border-radius:var(--ui-radius-pill);background:var(--ui-surface-muted);font-size:var(--ui-text-xs);font-weight:800}.review-actions{display:flex;gap:.5rem;flex-wrap:wrap}.evidence,.decision,.audit{display:grid;gap:.75rem;padding:1rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-lg);background:var(--ui-surface-muted)}.evidence header{display:flex;justify-content:space-between}.message-evidence{padding:.8rem;border-radius:var(--ui-radius-md);background:var(--ui-surface)}.message-evidence p{white-space:pre-wrap;overflow-wrap:anywhere}.decision-grid{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}.audit-row{display:flex;justify-content:space-between;gap:1rem;padding:.45rem 0;border-bottom:1px solid var(--ui-border)}.state{display:grid;place-items:center;align-content:center;gap:.4rem;min-height:10rem;padding:1rem;color:var(--ui-text-muted);text-align:center}.state--review{min-height:20rem}.notice{padding:.75rem 1rem;border-radius:var(--ui-radius-md);background:var(--ui-success-soft);color:var(--ui-success)}.notice--error{background:var(--ui-danger-soft);color:var(--ui-danger)}
@media(max-width:860px){.ts-hero,.workspace{grid-template-columns:1fr}.queue-panel{max-height:20rem;overflow:auto}.decision-grid{grid-template-columns:1fr}}@media(max-width:560px){.filters>*{width:100%}.review-head{display:grid}.review-actions{display:grid}.review-actions .ui-button{width:100%}}
</style>
