<template>
	<main class="invite-shell">
		<section class="invite-hero">
			<div>
				<span class="eyebrow">Приглашения</span>
				<h1>Закрытые пространства, куда вас позвали</h1>
				<p>Приглашение действует ограниченное время. Принятие всегда повторно проверяет доступ, блокировки и свободные места.</p>
			</div>
			<RouterLink class="ui-button ui-button--ghost" :to="{ name: 'people' }"><i class="fas fa-user-group"></i>Найти людей</RouterLink>
		</section>

		<section v-if="notice" class="notice" :class="`notice--${notice.type}`" role="status">
			<i :class="notice.type === 'error' ? 'fas fa-triangle-exclamation' : 'fas fa-circle-check'" aria-hidden="true"></i>
			<span>{{ notice.message }}</span>
		</section>

		<section v-if="loading" class="state-block" role="status">
			<i class="fas fa-circle-notch fa-spin"></i><strong>Проверяем приглашения…</strong>
		</section>

		<section v-else-if="invitations.length" class="invite-list" aria-label="Входящие приглашения">
			<article v-for="invitation in invitations" :key="invitation.uid" class="invite-card">
				<div class="invite-card__icon"><i class="fas fa-door-open"></i></div>
				<div class="invite-card__body">
					<span class="invite-card__from">{{ inviterLabel(invitation) }} приглашает вас</span>
					<h2>{{ invitation.space?.name || 'Пространство PubChat' }}</h2>
					<p>{{ invitation.space?.description || 'Закрытое пространство с собственными участниками и правилами.' }}</p>
					<div class="invite-meta">
						<span><i class="fas fa-hourglass-half"></i>До {{ formatExpiry(invitation.expires_at) }}</span>
						<RouterLink v-if="invitation.inviter?.account_uid" :to="{ name: 'UserProfile', params: { uid: invitation.inviter.account_uid } }"><i class="fas fa-user"></i>Открыть образ</RouterLink>
					</div>
				</div>
				<div class="invite-actions">
					<button type="button" class="ui-button" :disabled="busyUid === invitation.uid" @click="respond(invitation, 'accept')"><i class="fas fa-check"></i>Принять</button>
					<button type="button" class="ui-button ui-button--ghost" :disabled="busyUid === invitation.uid" @click="respond(invitation, 'decline')">Отклонить</button>
				</div>
			</article>
		</section>

		<section v-else class="state-block">
			<i class="fas fa-envelope-open-text"></i>
			<strong>Новых приглашений нет</strong>
			<span>Когда создатель или модератор позовёт вас в закрытое пространство, приглашение появится здесь.</span>
			<RouterLink class="ui-button" :to="{ name: 'chats' }">Открыть пространства</RouterLink>
		</section>
	</main>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';

import SpacesService from '@/API/SpacesService';

const router = useRouter();
const invitations = ref([]);
const loading = ref(true);
const busyUid = ref(null);
const notice = ref(null);

const loadInvitations = async () => {
	loading.value = true;
	try {
		const response = await SpacesService.invitations({ limit: 100, offset: 0 });
		invitations.value = response.data.invitations || [];
	} catch (error) {
		console.error('Не удалось загрузить приглашения:', error);
		notice.value = { type: 'error', message: 'Не удалось загрузить приглашения.' };
	} finally { loading.value = false; }
};

const respond = async (invitation, action) => {
	busyUid.value = invitation.uid;
	try {
		const response = await SpacesService.respondInvitation(invitation.uid, action);
		invitations.value = invitations.value.filter((item) => item.uid !== invitation.uid);
		if (action === 'accept') {
			const space = response.data.invitation?.space;
			if (space?.uid) {
				await router.push({ name: 'space', params: { uid: space.uid } });
				return;
			}
			notice.value = { type: 'success', message: 'Приглашение принято.' };
		} else {
			notice.value = { type: 'success', message: 'Приглашение отклонено.' };
		}
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		const message = type === 'space_invitation_not_active' ? 'Приглашение уже недействительно.' : type === 'space_full' ? 'В пространстве больше нет свободных мест.' : type === 'social_relationship_blocked' ? 'Вход недоступен из-за блокировки.' : 'Не удалось обработать приглашение.';
		notice.value = { type: 'error', message };
		if (type === 'space_invitation_not_active') invitations.value = invitations.value.filter((item) => item.uid !== invitation.uid);
	} finally { busyUid.value = null; }
};

const inviterLabel = (invitation) => invitation.inviter?.display_name || (invitation.inviter?.handle ? `@${invitation.inviter.handle}` : 'Участник PubChat');
const formatExpiry = (value) => new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }).format(new Date(value));

onMounted(loadInvitations);
</script>

<style scoped>
.invite-shell { display: grid; gap: var(--ui-space-5); padding-bottom: var(--ui-space-8); }.invite-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--ui-space-5); padding: clamp(1.4rem, 4vw, 2.5rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: linear-gradient(135deg, var(--ui-surface) 0%, var(--ui-warning-soft) 180%); }.invite-hero > div { max-width: 44rem; }.eyebrow { display: block; margin-bottom: .45rem; color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }.invite-hero h1 { margin: 0; font-size: clamp(1.7rem, 4vw, 2.8rem); letter-spacing: -.035em; line-height: 1.05; }.invite-hero p { margin: var(--ui-space-3) 0 0; color: var(--ui-text-muted); line-height: 1.6; }
.notice { display: flex; align-items: center; gap: var(--ui-space-2); padding: var(--ui-space-3) var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-success-soft); color: var(--ui-success); }.notice--error { background: var(--ui-danger-soft); color: var(--ui-danger); }
.invite-list { display: grid; gap: var(--ui-space-3); }.invite-card { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: var(--ui-space-4); padding: var(--ui-space-5); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); box-shadow: var(--ui-shadow-sm); }.invite-card__icon { width: 3.5rem; height: 3.5rem; display: grid; place-items: center; border-radius: 1rem; background: var(--ui-primary-soft); color: var(--ui-primary); font-size: var(--ui-text-xl); }.invite-card__body { min-width: 0; }.invite-card__from { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); font-weight: 700; }.invite-card h2 { margin: .2rem 0 .35rem; font-size: var(--ui-text-lg); }.invite-card p { margin: 0; color: var(--ui-text-muted); line-height: 1.5; }.invite-meta { display: flex; flex-wrap: wrap; gap: var(--ui-space-3); margin-top: var(--ui-space-3); color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }.invite-meta span, .invite-meta a { display: inline-flex; align-items: center; gap: .35rem; color: inherit; text-decoration: none; }.invite-meta a:hover { color: var(--ui-primary); }.invite-actions { display: flex; gap: var(--ui-space-2); }
.state-block { min-height: 20rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); padding: var(--ui-space-6); text-align: center; color: var(--ui-text-muted); }.state-block > i { font-size: 2rem; color: var(--ui-primary); }.state-block strong { color: var(--ui-text); font-size: var(--ui-text-lg); }.state-block span { max-width: 34rem; line-height: 1.5; }.state-block .ui-button { margin-top: var(--ui-space-2); }
@media (max-width: 760px) { .invite-hero { align-items: stretch; flex-direction: column; }.invite-card { grid-template-columns: auto minmax(0, 1fr); }.invite-actions { grid-column: 1 / -1; }.invite-actions .ui-button { flex: 1; } }
</style>
