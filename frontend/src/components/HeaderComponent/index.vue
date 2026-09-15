<template>
	<header class="app-topbar">
		<div class="topbar-inner container">
			<RouterLink class="brand" :to="{ name: 'chats' }" aria-label="PubChat — на главную">
				<span class="brand-mark" aria-hidden="true">P</span>
				<span class="brand-name">PubChat</span>
			</RouterLink>

			<nav v-if="isAuthenticated" class="desktop-nav" aria-label="Основная навигация">
				<RouterLink :to="{ name: 'chats' }">Пространства</RouterLink>
				<RouterLink :to="{ name: 'people' }">Люди</RouterLink>
				<RouterLink :to="{ name: 'messenger' }">Сообщения</RouterLink>
				<RouterLink v-if="spaceContextRoute" class="context-link" :to="spaceContextRoute"><i class="fas fa-landmark" aria-hidden="true"></i>Центр</RouterLink>
				<RouterLink v-if="spaceLifeRoute" class="context-link" :to="spaceLifeRoute"><i class="fas fa-mug-hot" aria-hidden="true"></i>Жизнь</RouterLink>
			</nav>

			<div class="topbar-actions">
				<template v-if="!isAuthenticated">
					<RouterLink class="guest-link" :to="{ name: 'login' }">Войти</RouterLink>
					<RouterLink class="ui-button signup-button" :to="{ name: 'registration' }">Создать образ</RouterLink>
				</template>

				<button class="icon-button" type="button" :aria-label="currentTheme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'" @click="toggleTheme">
					<i :class="currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon'" aria-hidden="true"></i>
				</button>

				<div v-if="isAuthenticated" class="persona-menu">
					<button class="persona-trigger" type="button" :aria-expanded="isDropdownOpen" aria-haspopup="menu" @click="toggleDropdown">
						<span class="persona-avatar">
							<img v-if="currentUser.avatar" :src="avatarUrl" alt="" />
							<span v-else>{{ avatarFallback }}</span>
						</span>
						<span class="persona-trigger__text">
							<strong>{{ currentUser.display_name || currentUser.username }}</strong>
							<small>{{ intentLabel }}</small>
						</span>
						<i class="fas fa-chevron-down persona-chevron" aria-hidden="true"></i>
					</button>

					<div v-if="isDropdownOpen" class="persona-dropdown" role="menu">
						<RouterLink role="menuitem" :to="profileRoute" @click="closeDropdown">
							<i class="fas fa-user-circle" aria-hidden="true"></i><span>Мой образ</span>
						</RouterLink>
						<RouterLink role="menuitem" :to="{ name: 'persona-style' }" @click="closeDropdown">
							<i class="fas fa-palette" aria-hidden="true"></i><span>Стиль образа</span>
						</RouterLink>
						<RouterLink role="menuitem" :to="{ name: 'achievements' }" @click="closeDropdown">
							<i class="fas fa-medal" aria-hidden="true"></i><span>Достижения</span>
						</RouterLink>
						<RouterLink v-if="spaceContextRoute" role="menuitem" :to="spaceContextRoute" @click="closeDropdown">
							<i class="fas fa-landmark" aria-hidden="true"></i><span>Центр пространства</span>
						</RouterLink>
						<RouterLink v-if="spaceLifeRoute" role="menuitem" :to="spaceLifeRoute" @click="closeDropdown">
							<i class="fas fa-mug-hot" aria-hidden="true"></i><span>Жизнь пространства</span>
						</RouterLink>
						<RouterLink role="menuitem" :to="{ name: 'invitations' }" @click="closeDropdown">
							<i class="fas fa-envelope-open-text" aria-hidden="true"></i><span>Приглашения</span>
						</RouterLink>
						<RouterLink role="menuitem" :to="{ name: 'safety' }" @click="closeDropdown">
							<i class="fas fa-shield-halved" aria-hidden="true"></i><span>Безопасность</span>
						</RouterLink>
						<RouterLink v-if="isAdmin" role="menuitem" :to="{ name: 'AdminDashboard' }" @click="closeDropdown">
							<i class="fas fa-user-shield" aria-hidden="true"></i><span>Управление</span>
						</RouterLink>
						<button role="menuitem" type="button" @click="handleLogout">
							<i class="fas fa-sign-out-alt" aria-hidden="true"></i><span>Выйти</span>
						</button>
					</div>
				</div>
			</div>
		</div>
	</header>

	<nav v-if="isAuthenticated" class="mobile-nav" aria-label="Мобильная навигация">
		<RouterLink :to="{ name: 'chats' }">
			<i class="fas fa-comments" aria-hidden="true"></i><span>Пространства</span>
		</RouterLink>
		<RouterLink :to="{ name: 'people' }">
			<i class="fas fa-user-group" aria-hidden="true"></i><span>Люди</span>
		</RouterLink>
		<RouterLink :to="{ name: 'messenger' }">
			<i class="fas fa-envelope" aria-hidden="true"></i><span>Сообщения</span>
		</RouterLink>
		<RouterLink :to="profileRoute">
			<i class="fas fa-user-circle" aria-hidden="true"></i><span>Профиль</span>
		</RouterLink>
	</nav>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { useStore } from 'vuex';

const router = useRouter();
const route = useRoute();
const store = useStore();
const currentTheme = ref('light');
const isDropdownOpen = ref(false);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

const isAuthenticated = computed(() => store.getters.isAuth);
const currentUser = computed(() => store.getters.getUser || {});
const isAdmin = computed(() => ['admin', 'superadmin'].includes(currentUser.value.global_role));
const profileRoute = computed(() => ({ name: 'UserProfile', params: { uid: currentUser.value.uid } }));
const spaceUid = computed(() => {
	const uid = route.params?.uid;
	if (!uid || !['space', 'space-community', 'space-life', 'space-moderation'].includes(String(route.name || ''))) return null;
	return uid;
});
const spaceContextRoute = computed(() => spaceUid.value ? { name: 'space-community', params: { uid: spaceUid.value } } : null);
const spaceLifeRoute = computed(() => spaceUid.value ? { name: 'space-life', params: { uid: spaceUid.value } } : null);
const avatarFallback = computed(() => (currentUser.value.display_name || currentUser.value.username || '?').slice(0, 1).toUpperCase());
const avatarUrl = computed(() => {
	const avatar = currentUser.value.avatar;
	if (!avatar) return '';
	if (/^https?:\/\//.test(avatar)) return avatar;
	return `${apiBaseUrl}${avatar}`;
});
const intentLabel = computed(() => ({
	open: 'Хочу пообщаться',
	meet: 'Открыт знакомствам',
	games: 'Ищу компанию для игры',
	friends: 'Только знакомые',
	quiet: 'Спокойный режим',
}[currentUser.value.social_intent] || 'В PubChat'));

const toggleDropdown = () => { isDropdownOpen.value = !isDropdownOpen.value; };
const closeDropdown = () => { isDropdownOpen.value = false; };

const handleLogout = async () => {
	closeDropdown();
	try {
		await store.dispatch('logout');
		await router.replace({ name: 'login' });
	} catch (error) {
		console.error('Ошибка при выходе:', error);
	}
};

const applyTheme = (theme) => {
	const root = document.documentElement;
	root.classList.remove('light-theme', 'dark-theme');
	root.classList.add(`${theme}-theme`);
	localStorage.setItem('theme', theme);
	currentTheme.value = theme;
};
const toggleTheme = () => applyTheme(currentTheme.value === 'dark' ? 'light' : 'dark');

onMounted(() => applyTheme(localStorage.getItem('theme') || 'light'));
</script>

<style scoped>
.app-topbar { position: sticky; top: 0; z-index: 120; border-bottom: 1px solid var(--ui-border); background: color-mix(in srgb, var(--ui-surface) 92%, transparent); backdrop-filter: blur(16px); }
.topbar-inner { min-height: 3.75rem; display: flex; align-items: center; gap: var(--ui-space-5); }
.brand { display: inline-flex; align-items: center; gap: var(--ui-space-2); color: var(--ui-text); text-decoration: none; font-weight: 800; letter-spacing: -0.02em; }
.brand-mark { width: 2rem; height: 2rem; display: grid; place-items: center; border-radius: 0.65rem; background: var(--ui-primary); color: var(--ui-primary-contrast); font-size: var(--ui-text-sm); }
.brand-name { font-size: var(--ui-text-lg); }
.desktop-nav { display: flex; align-items: center; gap: var(--ui-space-1); }
.desktop-nav a, .guest-link { min-height: 2.5rem; display: inline-flex; align-items: center; gap: .4rem; padding: 0 var(--ui-space-3); border-radius: var(--ui-radius-md); color: var(--ui-text-muted); text-decoration: none; font-size: var(--ui-text-sm); font-weight: 650; }
.desktop-nav a:hover, .desktop-nav a.router-link-active, .guest-link:hover { background: var(--ui-surface-muted); color: var(--ui-text); }
.desktop-nav .context-link { color: var(--ui-primary); }
.topbar-actions { margin-left: auto; display: flex; align-items: center; gap: var(--ui-space-2); }
.signup-button { min-height: 2.5rem; }
.icon-button { width: 2.5rem; height: 2.5rem; display: grid; place-items: center; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text-muted); cursor: pointer; }
.icon-button:hover { color: var(--ui-text); background: var(--ui-surface-muted); }
.persona-menu { position: relative; }
.persona-trigger { min-height: 2.75rem; display: flex; align-items: center; gap: var(--ui-space-2); padding: 0.2rem 0.45rem; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface); color: var(--ui-text); cursor: pointer; }
.persona-avatar { width: 2.15rem; height: 2.15rem; display: grid; place-items: center; overflow: hidden; border-radius: 50%; background: var(--ui-primary-soft); color: var(--ui-primary); font-weight: 800; }
.persona-avatar img { width: 100%; height: 100%; object-fit: cover; }
.persona-trigger__text { display: grid; max-width: 10rem; text-align: left; line-height: 1.1; }
.persona-trigger__text strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--ui-text-sm); }
.persona-trigger__text small { margin-top: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ui-text-subtle); font-size: 0.68rem; }
.persona-chevron { margin-right: var(--ui-space-1); color: var(--ui-text-subtle); font-size: 0.65rem; }
.persona-dropdown { position: absolute; top: calc(100% + var(--ui-space-2)); right: 0; width: 13rem; display: grid; padding: var(--ui-space-2); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface-raised); box-shadow: var(--ui-shadow-lg); }
.persona-dropdown a, .persona-dropdown button { min-height: 2.65rem; display: flex; align-items: center; gap: var(--ui-space-3); width: 100%; padding: 0 var(--ui-space-3); border: 0; border-radius: var(--ui-radius-md); background: transparent; color: var(--ui-text); text-decoration: none; text-align: left; cursor: pointer; }
.persona-dropdown a:hover, .persona-dropdown button:hover { background: var(--ui-surface-muted); }
.persona-dropdown i { width: 1rem; color: var(--ui-text-muted); }
.mobile-nav { display: none; }
@media (max-width: 720px) {
	.app-topbar { position: sticky; }
	.topbar-inner { min-height: 3.35rem; padding-inline: var(--ui-space-3); }
	.brand-name, .desktop-nav, .persona-trigger__text, .persona-chevron, .signup-button { display: none; }
	.persona-trigger { border: 0; padding: 0; }
	.mobile-nav { position: fixed; left: 0; right: 0; bottom: 0; z-index: 130; min-height: 4.15rem; display: grid; grid-template-columns: repeat(4, 1fr); padding: 0.35rem max(0.35rem, env(safe-area-inset-right)) calc(0.35rem + env(safe-area-inset-bottom)) max(0.35rem, env(safe-area-inset-left)); border-top: 1px solid var(--ui-border); background: color-mix(in srgb, var(--ui-surface) 95%, transparent); backdrop-filter: blur(18px); }
	.mobile-nav a { display: grid; place-items: center; align-content: center; gap: 0.2rem; border-radius: var(--ui-radius-md); color: var(--ui-text-subtle); text-decoration: none; font-size: 0.64rem; font-weight: 650; }
	.mobile-nav a i { font-size: 1.05rem; }
	.mobile-nav a.router-link-active { background: var(--ui-primary-soft); color: var(--ui-primary); }
	.persona-dropdown { position: fixed; top: auto; right: var(--ui-space-3); bottom: calc(4.7rem + env(safe-area-inset-bottom)); left: var(--ui-space-3); width: auto; }
}
</style>
