<template>
	<aside class="space-panel" :class="{ active: isActive }" aria-label="Информация о пространстве">
		<header class="space-panel__header">
			<div>
				<span>О пространстве</span>
				<strong>{{ roomInfo.name }}</strong>
			</div>
			<button type="button" class="icon-button" aria-label="Закрыть панель" @click="closeSidebar">
				<i class="fas fa-xmark" aria-hidden="true"></i>
			</button>
		</header>

		<div class="panel-tabs" role="tablist" aria-label="Разделы пространства">
			<button type="button" role="tab" :aria-selected="activeTab === 'info'" :class="{ active: activeTab === 'info' }" @click="activeTab = 'info'">
				Обзор
			</button>
			<button type="button" role="tab" :aria-selected="activeTab === 'people'" :class="{ active: activeTab === 'people' }" @click="activeTab = 'people'">
				Люди <span class="count-badge">{{ users.length }}</span>
			</button>
		</div>

		<section v-if="activeTab === 'info'" class="panel-content">
			<div class="space-summary">
				<p>{{ roomInfo.description || 'У этого пространства пока нет описания.' }}</p>
				<div v-if="tags.length" class="tag-list">
					<span v-for="tag in tags" :key="tag" class="ui-chip">{{ tag }}</span>
				</div>
			</div>

			<dl class="space-facts">
				<div v-if="owner">
					<dt>Создатель</dt>
					<dd>
						<RouterLink :to="`/profile/${owner.uid}`">{{ owner.display_name || owner.username }}</RouterLink>
					</dd>
				</div>
				<div v-if="roomInfo.region || roomInfo.country">
					<dt>Регион</dt>
					<dd>{{ [roomInfo.region, roomInfo.country].filter(Boolean).join(', ') }}</dd>
				</div>
				<div v-if="roomInfo.created_at">
					<dt>Здесь с</dt>
					<dd>{{ formatDate(roomInfo.created_at) }}</dd>
				</div>
			</dl>

			<div class="panel-note">
				<i class="fas fa-handshake" aria-hidden="true"></i>
				<div>
					<strong>Общие правила, своя атмосфера</strong>
					<span>Роли действуют только внутри этого пространства и не являются статусом человека во всём PubChat.</span>
				</div>
			</div>
		</section>

		<section v-else class="panel-content panel-content--people">
			<div v-if="users.length" class="people-list">
				<div v-for="user in users" :key="user.uid" class="person-row">
					<RouterLink :to="`/profile/${user.uid}`" class="person-link">
						<span class="person-avatar">
							<img v-if="user.avatar" :src="resolveAvatar(user.avatar)" alt="" />
							<span v-else>{{ avatarFallback(user.display_name || user.username) }}</span>
						</span>
						<span class="person-copy">
							<strong>{{ user.display_name || user.username }}</strong>
							<small v-if="user.social_intent">{{ intentLabel(user.social_intent) }}</small>
						</span>
					</RouterLink>

					<span v-if="user.uid === roomInfo.owner_uid" class="role-chip role-chip--owner">Создатель</span>
					<span v-else-if="isModerator(user.uid)" class="role-chip">Модератор</span>

					<div
						v-if="canManage(user.uid)"
						class="person-actions"
					>
						<button type="button" class="more-button" :aria-expanded="activeUserMenu === user.uid" aria-label="Действия с участником" @click.stop="toggleUserMenu(user.uid)">
							<i class="fas fa-ellipsis" aria-hidden="true"></i>
						</button>
						<div v-if="activeUserMenu === user.uid" class="person-menu">
							<button v-if="isOwner" type="button" @click="toggleModeratorStatus(user.uid)">
								<i class="fas fa-user-shield" aria-hidden="true"></i>
								{{ isModerator(user.uid) ? 'Снять роль модератора' : 'Сделать модератором' }}
							</button>
							<button type="button" class="person-menu__danger" @click="restrictUser(user.uid)">
								<i class="fas fa-user-slash" aria-hidden="true"></i>
								Ограничить доступ
							</button>
						</div>
					</div>
				</div>
			</div>

			<div v-else class="people-empty">
				<i class="fas fa-couch" aria-hidden="true"></i>
				<strong>Пока никого</strong>
				<span>Когда люди зайдут в пространство, они появятся здесь.</span>
			</div>
		</section>
	</aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { useStore } from 'vuex';

import UsersServices from '@/API/UsersService';

const props = defineProps({
	isActive: { type: Boolean, default: false },
	roomInfo: { type: Object, default: () => ({}) },
	users: { type: Array, default: () => [] },
});

const emit = defineEmits(['close', 'user-banned', 'moderator-changed']);
const store = useStore();
const owner = ref(null);
const activeTab = ref('info');
const activeUserMenu = ref(null);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

const currentUserUid = computed(() => store.getters.getUser?.uid);
const isOwner = computed(() => currentUserUid.value === props.roomInfo.owner_uid);
const isCurrentUserModerator = computed(() => isModerator(currentUserUid.value));
const tags = computed(() => String(props.roomInfo.tags || '').split(',').map((tag) => tag.trim()).filter(Boolean));

const isModerator = (uid) => props.roomInfo.moderators?.includes(uid) || false;
const canManage = (userUid) => (
	(isOwner.value || isCurrentUserModerator.value)
	&& userUid !== currentUserUid.value
	&& userUid !== props.roomInfo.owner_uid
);

const resolveAvatar = (avatar) => /^https?:\/\//.test(avatar) ? avatar : `${apiBaseUrl}${avatar}`;
const avatarFallback = (value = '?') => String(value || '?').slice(0, 1).toUpperCase();
const intentLabel = (intent) => ({
	open: 'Хочет пообщаться',
	meet: 'Открыт новым знакомствам',
	games: 'Ищет компанию для игры',
	friends: 'Общается со знакомыми',
	quiet: 'Спокойный режим',
}[intent] || 'В PubChat');

const toggleUserMenu = (userId) => {
	activeUserMenu.value = activeUserMenu.value === userId ? null : userId;
};

const toggleModeratorStatus = (userId) => {
	const action = isModerator(userId) ? 'remove_moderator' : 'add_moderator';
	emit('moderator-changed', { userId, isModerator: action === 'add_moderator' });
	activeUserMenu.value = null;
};

const restrictUser = (userId) => {
	emit('user-banned', userId);
	activeUserMenu.value = null;
};

const closeSidebar = () => emit('close');
const formatDate = (dateString) => new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(dateString));

const loadOwner = async (ownerUid) => {
	owner.value = null;
	if (!ownerUid) return;
	try {
		const response = await UsersServices.get_user_by_uid(ownerUid);
		if (response.data.status === 'ok') owner.value = response.data.user;
	} catch (error) {
		console.error('Не удалось загрузить Persona создателя пространства:', error);
	}
};

watch(() => props.roomInfo.owner_uid, loadOwner, { immediate: true });
watch(() => props.roomInfo.uid, () => {
	activeTab.value = 'info';
	activeUserMenu.value = null;
});
</script>

<style scoped>
.space-panel {
	position: relative;
	width: 20rem;
	min-width: 20rem;
	height: 100%;
	display: flex;
	flex-direction: column;
	border-left: 1px solid var(--ui-border);
	background: var(--ui-surface);
}

.space-panel__header { min-height: 4.25rem; display: flex; align-items: center; justify-content: space-between; gap: var(--ui-space-3); padding: var(--ui-space-3) var(--ui-space-4); }
.space-panel__header > div { min-width: 0; display: grid; }
.space-panel__header span { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }
.space-panel__header strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.icon-button { width: 2.5rem; height: 2.5rem; display: grid; place-items: center; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text-muted); cursor: pointer; }
.icon-button:hover { background: var(--ui-surface-muted); color: var(--ui-text); }

.panel-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ui-space-1); margin: 0 var(--ui-space-3); padding: var(--ui-space-1); border-radius: var(--ui-radius-md); background: var(--ui-surface-muted); }
.panel-tabs button { min-height: 2.35rem; display: flex; align-items: center; justify-content: center; gap: var(--ui-space-1); border: 0; border-radius: calc(var(--ui-radius-md) - 0.2rem); background: transparent; color: var(--ui-text-muted); font: inherit; font-size: var(--ui-text-sm); font-weight: 700; cursor: pointer; }
.panel-tabs button.active { background: var(--ui-surface); color: var(--ui-text); box-shadow: var(--ui-shadow-sm); }
.count-badge { min-width: 1.25rem; padding: 0 0.3rem; border-radius: var(--ui-radius-pill); background: var(--ui-primary-soft); color: var(--ui-primary); font-size: 0.68rem; }

.panel-content { min-height: 0; flex: 1; overflow-y: auto; padding: var(--ui-space-4); }
.space-summary p { margin: 0; color: var(--ui-text-muted); line-height: 1.55; }
.tag-list { display: flex; flex-wrap: wrap; gap: var(--ui-space-1); margin-top: var(--ui-space-3); }
.space-facts { display: grid; gap: var(--ui-space-3); margin: var(--ui-space-5) 0; }
.space-facts div { display: grid; gap: 0.15rem; }
.space-facts dt { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }
.space-facts dd { margin: 0; color: var(--ui-text); font-size: var(--ui-text-sm); }
.space-facts a { color: var(--ui-primary); text-decoration: none; font-weight: 700; }
.space-facts a:hover { text-decoration: underline; }
.panel-note { display: flex; gap: var(--ui-space-3); padding: var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface-soft); color: var(--ui-text-muted); }
.panel-note > i { margin-top: 0.15rem; color: var(--ui-primary); }
.panel-note div { display: grid; gap: 0.2rem; }
.panel-note strong { color: var(--ui-text); font-size: var(--ui-text-sm); }
.panel-note span { font-size: var(--ui-text-xs); line-height: 1.45; }

.panel-content--people { padding-inline: var(--ui-space-2); }
.people-list { display: grid; gap: var(--ui-space-1); }
.person-row { position: relative; min-height: 3.6rem; display: flex; align-items: center; gap: var(--ui-space-2); padding: var(--ui-space-2); border-radius: var(--ui-radius-lg); }
.person-row:hover { background: var(--ui-surface-muted); }
.person-link { min-width: 0; flex: 1; display: flex; align-items: center; gap: var(--ui-space-2); color: var(--ui-text); text-decoration: none; }
.person-avatar { width: 2.4rem; height: 2.4rem; display: grid; place-items: center; flex: 0 0 auto; overflow: hidden; border-radius: 50%; background: var(--ui-primary-soft); color: var(--ui-primary); font-weight: 800; }
.person-avatar img { width: 100%; height: 100%; object-fit: cover; }
.person-copy { min-width: 0; display: grid; }
.person-copy strong, .person-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.person-copy small { color: var(--ui-text-subtle); font-size: 0.7rem; }
.role-chip { flex: 0 0 auto; padding: 0.2rem 0.45rem; border-radius: var(--ui-radius-pill); background: var(--ui-info-soft); color: var(--ui-info); font-size: 0.65rem; font-weight: 700; }
.role-chip--owner { background: var(--ui-primary-soft); color: var(--ui-primary); }
.person-actions { position: relative; }
.more-button { width: 2rem; height: 2rem; display: grid; place-items: center; border: 0; border-radius: var(--ui-radius-md); background: transparent; color: var(--ui-text-subtle); cursor: pointer; }
.more-button:hover { background: var(--ui-surface); color: var(--ui-text); }
.person-menu { position: absolute; right: 0; top: calc(100% + var(--ui-space-1)); z-index: 20; width: 14rem; display: grid; padding: var(--ui-space-1); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface-raised); box-shadow: var(--ui-shadow-lg); }
.person-menu button { min-height: 2.55rem; display: flex; align-items: center; gap: var(--ui-space-2); padding: 0 var(--ui-space-3); border: 0; border-radius: var(--ui-radius-md); background: transparent; color: var(--ui-text); text-align: left; cursor: pointer; }
.person-menu button:hover { background: var(--ui-surface-muted); }
.person-menu .person-menu__danger { color: var(--ui-danger); }
.people-empty { min-height: 14rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); text-align: center; color: var(--ui-text-muted); }
.people-empty i { font-size: var(--ui-text-xl); color: var(--ui-primary); }
.people-empty strong { color: var(--ui-text); }
.people-empty span { max-width: 14rem; font-size: var(--ui-text-xs); }

@media (max-width: 1099px) {
	.space-panel { position: fixed; top: 4rem; right: 0; bottom: 4.7rem; z-index: 115; width: min(22rem, calc(100vw - 2rem)); min-width: 0; height: auto; transform: translateX(110%); box-shadow: var(--ui-shadow-lg); transition: transform var(--ui-motion-normal) var(--ui-ease); }
	.space-panel.active { transform: translateX(0); }
}
</style>
