<template>
	<main class="people-shell">
		<section class="people-hero">
			<div>
				<span class="eyebrow">Люди PubChat</span>
				<h1>Находите людей по атмосфере, а не по рейтингу</h1>
				<p>Публичные образы и люди из общих пространств. Приватность и блокировки применяются сервером до выдачи результатов.</p>
			</div>
			<RouterLink class="ui-button ui-button--ghost" :to="{ name: 'invitations' }">
				<i class="fas fa-envelope-open-text" aria-hidden="true"></i>
				Приглашения
			</RouterLink>
		</section>

		<section v-if="manageableSpaces.length" class="invite-context">
			<div>
				<strong>Пригласить в пространство</strong>
				<span>Выберите пространство — на карточках людей появится действие приглашения.</span>
			</div>
			<select v-model="inviteSpaceUid" aria-label="Пространство для приглашения">
				<option value="">Не выбрано</option>
				<option v-for="space in manageableSpaces" :key="space.uid" :value="space.uid">{{ space.name }}</option>
			</select>
		</section>

		<section class="people-toolbar" aria-label="Поиск людей">
			<form class="search-box" @submit.prevent="loadPeople">
				<i class="fas fa-magnifying-glass" aria-hidden="true"></i>
				<input v-model.trim="searchQuery" type="search" maxlength="80" placeholder="Имя, @handle или интересы" />
				<button v-if="searchQuery" type="button" aria-label="Очистить поиск" @click="clearSearch"><i class="fas fa-xmark"></i></button>
			</form>
			<div class="intent-filter" role="list" aria-label="Намерение общения">
				<button v-for="item in intentOptions" :key="item.value || 'all'" type="button" class="filter-chip" :class="{ active: intent === item.value }" @click="setIntent(item.value)">{{ item.label }}</button>
			</div>
		</section>

		<section v-if="notice" class="notice" :class="`notice--${notice.type}`" role="status">
			<i :class="notice.type === 'error' ? 'fas fa-triangle-exclamation' : 'fas fa-circle-check'" aria-hidden="true"></i>
			<span>{{ notice.message }}</span>
		</section>

		<section v-if="loading" class="state-block" role="status">
			<i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i>
			<strong>Ищем людей…</strong>
		</section>

		<section v-else-if="people.length" class="people-grid" aria-label="Люди PubChat">
			<article v-for="person in people" :key="person.account_uid" class="person-card">
				<div class="person-card__identity">
					<RouterLink :to="{ name: 'UserProfile', params: { uid: person.account_uid } }" class="person-avatar">
						<img v-if="person.avatar" :src="resolveAvatar(person.avatar)" alt="" />
						<span v-else>{{ avatarFallback(person.display_name || person.handle) }}</span>
					</RouterLink>
					<div class="person-title">
						<RouterLink :to="{ name: 'UserProfile', params: { uid: person.account_uid } }"><strong>{{ person.display_name || person.handle || 'Участник PubChat' }}</strong></RouterLink>
						<span v-if="person.handle">@{{ person.handle }}</span>
					</div>
					<span class="intent-badge">{{ intentLabel(person.social_intent) }}</span>
				</div>

				<p class="person-bio">{{ person.bio || 'Пока без описания — знакомство можно начать с общего пространства.' }}</p>
				<div v-if="person.city || person.country" class="person-location"><i class="fas fa-location-dot" aria-hidden="true"></i>{{ [person.city, person.country].filter(Boolean).join(', ') }}</div>

				<div class="relationship-state">
					<span v-if="person.relationship?.friends"><i class="fas fa-user-group"></i> Вы друзья</span>
					<span v-else-if="person.relationship?.friend_request === 'incoming'"><i class="fas fa-user-plus"></i> Хочет дружить</span>
					<span v-else-if="person.relationship?.friend_request === 'outgoing'"><i class="fas fa-clock"></i> Запрос отправлен</span>
					<span v-if="person.relationship?.followed_by"><i class="fas fa-arrow-left"></i> Следит за вами</span>
				</div>

				<footer class="person-actions">
					<button type="button" class="ui-button ui-button--ghost" :disabled="busyUid === person.account_uid" @click="toggleFollow(person)">
						<i :class="person.relationship?.following ? 'fas fa-user-check' : 'fas fa-eye'" aria-hidden="true"></i>
						{{ person.relationship?.following ? 'Отписаться' : 'Следить' }}
					</button>
					<button type="button" class="ui-button" :class="{ 'ui-button--ghost': person.relationship?.friends || person.relationship?.friend_request }" :disabled="busyUid === person.account_uid" @click="friendAction(person)">
						{{ friendActionLabel(person) }}
					</button>
					<button v-if="inviteSpaceUid" type="button" class="ui-button ui-button--ghost" :disabled="busyUid === person.account_uid" @click="invitePerson(person)">
						<i class="fas fa-envelope" aria-hidden="true"></i>Пригласить
					</button>
					<button type="button" class="icon-danger" :disabled="busyUid === person.account_uid" aria-label="Заблокировать пользователя" @click="blockPerson(person)"><i class="fas fa-user-slash"></i></button>
				</footer>
			</article>
		</section>

		<section v-else class="state-block">
			<i class="fas fa-user-group" aria-hidden="true"></i>
			<strong>Никого не нашли</strong>
			<span>Измените запрос или фильтр. Закрытые и заблокированные профили намеренно не попадают в выдачу.</span>
		</section>

		<button v-if="people.length < total && !loading" type="button" class="load-more" :disabled="loadingMore" @click="loadMore">{{ loadingMore ? 'Загружаем…' : 'Показать ещё' }}</button>
	</main>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import SocialService from '@/API/SocialService';
import SpacesService from '@/API/SpacesService';

const route = useRoute();
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const people = ref([]);
const total = ref(0);
const loading = ref(true);
const loadingMore = ref(false);
const searchQuery = ref('');
const intent = ref(null);
const manageableSpaces = ref([]);
const inviteSpaceUid = ref('');
const busyUid = ref(null);
const notice = ref(null);

const intentOptions = [
	{ value: null, label: 'Все' },
	{ value: 'open', label: 'Пообщаться' },
	{ value: 'meet', label: 'Знакомства' },
	{ value: 'games', label: 'Игры' },
	{ value: 'friends', label: 'Знакомые' },
	{ value: 'quiet', label: 'Спокойно' },
];

const showNotice = (message, type = 'success') => {
	notice.value = { message, type };
	window.setTimeout(() => { if (notice.value?.message === message) notice.value = null; }, 3500);
};

const loadManageableSpaces = async () => {
	try {
		const response = await SpacesService.list({ limit: 50 });
		manageableSpaces.value = (response.data.spaces || []).filter((space) => space.can_manage && space.viewer_membership?.status === 'active');
		const requested = String(route.query.inviteTo || '');
		if (requested && manageableSpaces.value.some((space) => space.uid === requested)) inviteSpaceUid.value = requested;
	} catch (error) {
		console.error('Не удалось загрузить пространства для приглашений:', error);
	}
};

const loadPeople = async ({ append = false } = {}) => {
	append ? loadingMore.value = true : loading.value = true;
	try {
		const offset = append ? people.value.length : 0;
		const response = await SocialService.discover({ q: searchQuery.value || undefined, social_intent: intent.value || undefined, limit: 30, offset });
		const items = response.data.people || [];
		people.value = append ? [...people.value, ...items] : items;
		total.value = response.data.pagination?.total ?? people.value.length;
	} catch (error) {
		console.error('Не удалось загрузить людей:', error);
		showNotice('Не удалось загрузить людей. Попробуйте ещё раз.', 'error');
	} finally {
		loading.value = false;
		loadingMore.value = false;
	}
};

const patchRelationship = (person, relationship) => { person.relationship = { ...(person.relationship || {}), ...relationship }; };
const toggleFollow = async (person) => {
	busyUid.value = person.account_uid;
	try {
		const response = person.relationship?.following ? await SocialService.unfollow(person.account_uid) : await SocialService.follow(person.account_uid);
		patchRelationship(person, response.data.relationship);
	} catch (error) {
		showNotice('Не удалось изменить подписку.', 'error');
	} finally { busyUid.value = null; }
};

const friendAction = async (person) => {
	let action = 'request';
	if (person.relationship?.friends) action = 'remove';
	else if (person.relationship?.friend_request === 'incoming') action = 'accept';
	else if (person.relationship?.friend_request === 'outgoing') action = 'remove';
	busyUid.value = person.account_uid;
	try {
		const response = await SocialService.friendAction(person.account_uid, action);
		patchRelationship(person, response.data.relationship);
	} catch (error) {
		showNotice('Не удалось изменить статус дружбы.', 'error');
	} finally { busyUid.value = null; }
};

const invitePerson = async (person) => {
	if (!inviteSpaceUid.value) return;
	busyUid.value = person.account_uid;
	try {
		await SpacesService.invite(inviteSpaceUid.value, person.account_uid);
		const space = manageableSpaces.value.find((item) => item.uid === inviteSpaceUid.value);
		showNotice(`Приглашение в «${space?.name || 'пространство'}» отправлено.`);
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		const message = type === 'invitee_already_member' ? 'Этот человек уже участник пространства.' : type === 'social_relationship_blocked' ? 'Приглашение недоступно из-за блокировки.' : 'Не удалось отправить приглашение.';
		showNotice(message, 'error');
	} finally { busyUid.value = null; }
};

const blockPerson = async (person) => {
	busyUid.value = person.account_uid;
	try {
		await SocialService.block(person.account_uid);
		people.value = people.value.filter((item) => item.account_uid !== person.account_uid);
		total.value = Math.max(0, total.value - 1);
		showNotice('Пользователь заблокирован и скрыт из discovery.');
	} catch (error) {
		showNotice('Не удалось заблокировать пользователя.', 'error');
	} finally { busyUid.value = null; }
};

const setIntent = async (value) => { intent.value = value; await loadPeople(); };
const clearSearch = async () => { searchQuery.value = ''; await loadPeople(); };
const loadMore = () => loadPeople({ append: true });
const friendActionLabel = (person) => person.relationship?.friends ? 'Убрать из друзей' : person.relationship?.friend_request === 'incoming' ? 'Принять дружбу' : person.relationship?.friend_request === 'outgoing' ? 'Отменить запрос' : 'Добавить в друзья';
const intentLabel = (value) => ({ open: 'Хочет пообщаться', meet: 'Открыт знакомствам', games: 'Ищет компанию для игры', friends: 'Общается со знакомыми', quiet: 'Спокойный режим' }[value] || 'Открыт общению');
const resolveAvatar = (avatar) => /^https?:\/\//.test(avatar) ? avatar : `${apiBaseUrl}${avatar}`;
const avatarFallback = (value = '?') => String(value || '?').slice(0, 1).toUpperCase();

onMounted(async () => { await Promise.all([loadManageableSpaces(), loadPeople()]); });
</script>

<style scoped>
.people-shell { display: grid; gap: var(--ui-space-5); padding-bottom: var(--ui-space-8); }
.people-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--ui-space-5); padding: clamp(1.4rem, 4vw, 2.5rem); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: linear-gradient(135deg, var(--ui-surface) 0%, var(--ui-info-soft) 170%); }
.people-hero > div { max-width: 45rem; }.eyebrow { display: block; margin-bottom: .45rem; color: var(--ui-primary); font-size: var(--ui-text-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.people-hero h1 { margin: 0; font-size: clamp(1.75rem, 4vw, 2.8rem); line-height: 1.05; letter-spacing: -.035em; }.people-hero p { margin: var(--ui-space-3) 0 0; color: var(--ui-text-muted); line-height: 1.6; }
.invite-context { display: flex; align-items: center; justify-content: space-between; gap: var(--ui-space-4); padding: var(--ui-space-4); border: 1px solid color-mix(in srgb, var(--ui-primary) 25%, var(--ui-border)); border-radius: var(--ui-radius-lg); background: var(--ui-primary-soft); }.invite-context div { display: grid; gap: .2rem; }.invite-context span { color: var(--ui-text-muted); font-size: var(--ui-text-sm); }.invite-context select { min-width: min(100%, 18rem); min-height: 2.7rem; padding: 0 var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text); }
.people-toolbar { display: grid; gap: var(--ui-space-3); }.search-box { min-height: 3.2rem; display: flex; align-items: center; gap: var(--ui-space-3); padding: 0 var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface); }.search-box input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: var(--ui-text); font: inherit; }.search-box button { border: 0; background: transparent; color: var(--ui-text-subtle); cursor: pointer; }
.intent-filter { display: flex; gap: var(--ui-space-2); overflow-x: auto; scrollbar-width: none; }.filter-chip { flex: 0 0 auto; min-height: 2.3rem; padding: 0 var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface); color: var(--ui-text-muted); font: inherit; font-size: var(--ui-text-sm); font-weight: 700; cursor: pointer; }.filter-chip.active { background: var(--ui-primary-soft); color: var(--ui-primary); border-color: color-mix(in srgb, var(--ui-primary) 35%, var(--ui-border)); }
.notice { display: flex; align-items: center; gap: var(--ui-space-2); padding: var(--ui-space-3) var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-success-soft); color: var(--ui-success); }.notice--error { background: var(--ui-danger-soft); color: var(--ui-danger); }
.people-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--ui-space-4); }.person-card { display: grid; gap: var(--ui-space-3); padding: var(--ui-space-5); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-xl); background: var(--ui-surface); box-shadow: var(--ui-shadow-sm); }.person-card__identity { display: flex; align-items: center; gap: var(--ui-space-3); }.person-avatar { width: 3.3rem; height: 3.3rem; display: grid; place-items: center; flex: 0 0 auto; overflow: hidden; border-radius: 50%; background: var(--ui-primary-soft); color: var(--ui-primary); text-decoration: none; font-weight: 800; font-size: var(--ui-text-lg); }.person-avatar img { width: 100%; height: 100%; object-fit: cover; }.person-title { min-width: 0; flex: 1; display: grid; }.person-title a { overflow: hidden; color: var(--ui-text); text-decoration: none; text-overflow: ellipsis; white-space: nowrap; }.person-title span { color: var(--ui-text-subtle); font-size: var(--ui-text-sm); }.intent-badge { flex: 0 0 auto; max-width: 10rem; padding: .3rem .55rem; border-radius: var(--ui-radius-pill); background: var(--ui-surface-muted); color: var(--ui-text-muted); font-size: .68rem; font-weight: 700; }.person-bio { min-height: 2.8rem; margin: 0; color: var(--ui-text-muted); line-height: 1.5; }.person-location, .relationship-state { display: flex; flex-wrap: wrap; gap: var(--ui-space-3); color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }.relationship-state span { display: inline-flex; align-items: center; gap: .3rem; }.person-actions { display: flex; flex-wrap: wrap; gap: var(--ui-space-2); padding-top: var(--ui-space-2); border-top: 1px solid var(--ui-border); }.person-actions .ui-button { min-height: 2.45rem; padding-inline: var(--ui-space-3); font-size: var(--ui-text-sm); }.icon-danger { width: 2.45rem; height: 2.45rem; display: grid; place-items: center; margin-left: auto; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: transparent; color: var(--ui-text-subtle); cursor: pointer; }.icon-danger:hover { border-color: color-mix(in srgb, var(--ui-danger) 30%, var(--ui-border)); background: var(--ui-danger-soft); color: var(--ui-danger); }
.state-block { min-height: 18rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); padding: var(--ui-space-6); text-align: center; color: var(--ui-text-muted); }.state-block > i { font-size: 2rem; color: var(--ui-primary); }.state-block strong { color: var(--ui-text); font-size: var(--ui-text-lg); }.load-more { justify-self: center; min-height: 2.7rem; padding: 0 var(--ui-space-4); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface); color: var(--ui-text); cursor: pointer; }
@media (max-width: 820px) { .people-hero, .invite-context { align-items: stretch; flex-direction: column; }.people-grid { grid-template-columns: 1fr; }.invite-context select { width: 100%; }.intent-badge { display: none; } }
</style>
