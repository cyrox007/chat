<template>
	<aside class="space-nav" aria-label="Мои пространства">
		<header class="space-nav__header">
			<div>
				<span>Места</span>
				<strong>Пространства</strong>
			</div>
			<div class="space-nav__actions">
				<button type="button" aria-label="Найти или создать пространство" @click="emitDiscover">
					<i class="fas fa-compass" aria-hidden="true"></i>
				</button>
				<button class="space-nav__close" type="button" aria-label="Закрыть" @click="closeSidebar">
					<i class="fas fa-xmark" aria-hidden="true"></i>
				</button>
			</div>
		</header>

		<label class="space-nav__search">
			<i class="fas fa-magnifying-glass" aria-hidden="true"></i>
			<input v-model.trim="query" type="search" placeholder="Найти среди ваших мест" />
		</label>

		<div class="space-nav__list">
			<button
				v-for="space in filteredSpaces"
				:key="space.uid"
				type="button"
				class="space-nav__item"
				:class="{ active: space.uid === activeSpaceUid }"
				@click="selectSpace(space)"
			>
				<span class="space-nav__glyph"><i :class="purposeIcon(space.purpose)" aria-hidden="true"></i></span>
				<span class="space-nav__copy">
					<strong>{{ space.name }}</strong>
					<small>{{ metaLabel(space) }}</small>
				</span>
				<i class="fas fa-chevron-right space-nav__chevron" aria-hidden="true"></i>
			</button>

			<div v-if="!filteredSpaces.length" class="space-nav__empty">
				<i class="fas fa-compass" aria-hidden="true"></i>
				<strong>{{ query ? 'Ничего не найдено' : 'Пока нет других мест' }}</strong>
				<span v-if="!query">Откройте discovery, чтобы найти или создать пространство.</span>
			</div>
		</div>

		<footer class="space-nav__footer">
			<button type="button" class="ui-button" @click="emitDiscover">
				<i class="fas fa-plus" aria-hidden="true"></i>
				Найти или создать
			</button>
		</footer>
	</aside>
</template>

<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
	isActive: { type: Boolean, default: false },
	spaces: { type: Array, default: () => [] },
	activeSpaceUid: { type: String, default: null },
});

const emit = defineEmits(['close', 'switch-space', 'discover']);
const query = ref('');

const filteredSpaces = computed(() => {
	const needle = query.value.toLocaleLowerCase();
	if (!needle) return props.spaces;
	return props.spaces.filter((space) => String(space.name || '').toLocaleLowerCase().includes(needle));
});

const closeSidebar = () => emit('close');
const selectSpace = (space) => emit('switch-space', space);
const emitDiscover = () => emit('discover');

const purposeIcon = (purpose) => ({
	community: 'fas fa-people-group',
	conversation: 'fas fa-comments',
	meet_people: 'fas fa-handshake',
	games: 'fas fa-gamepad',
	local: 'fas fa-location-dot',
}[purpose] || 'fas fa-comments');

const metaLabel = (space) => {
	const membership = space.viewer_membership;
	if (membership?.role === 'owner') return `Ваше · ${space.member_count || 1} участников`;
	if (membership?.role === 'moderator') return `Модератор · ${space.member_count || 0} участников`;
	return `${space.member_count || 0} участников`;
};
</script>

<style scoped>
.space-nav { position: relative; width: 19rem; min-width: 19rem; height: 100%; display: flex; flex-direction: column; border-right: 1px solid var(--ui-border); background: var(--ui-surface); }
.space-nav__header { min-height: 4.25rem; display: flex; align-items: center; justify-content: space-between; gap: var(--ui-space-3); padding: var(--ui-space-3) var(--ui-space-4); }
.space-nav__header > div:first-child { min-width: 0; display: grid; }
.space-nav__header span { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }
.space-nav__header strong { color: var(--ui-text); }
.space-nav__actions { display: flex; gap: var(--ui-space-1); }
.space-nav__actions button { width: 2.35rem; height: 2.35rem; display: grid; place-items: center; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-md); background: var(--ui-surface); color: var(--ui-text-muted); cursor: pointer; }
.space-nav__actions button:hover { background: var(--ui-surface-muted); color: var(--ui-text); }
.space-nav__close { display: none !important; }
.space-nav__search { min-height: 2.65rem; display: flex; align-items: center; gap: var(--ui-space-2); margin: 0 var(--ui-space-3) var(--ui-space-3); padding: 0 var(--ui-space-3); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-pill); background: var(--ui-surface-soft); color: var(--ui-text-subtle); }
.space-nav__search input { min-width: 0; width: 100%; border: 0; outline: 0; background: transparent; color: var(--ui-text); font: inherit; font-size: var(--ui-text-sm); }
.space-nav__list { min-height: 0; flex: 1; overflow-y: auto; display: grid; align-content: start; gap: var(--ui-space-1); padding: 0 var(--ui-space-2) var(--ui-space-3); }
.space-nav__item { width: 100%; min-height: 4rem; display: grid; grid-template-columns: 2.35rem minmax(0, 1fr) auto; align-items: center; gap: var(--ui-space-2); padding: var(--ui-space-2); border: 0; border-radius: var(--ui-radius-lg); background: transparent; color: var(--ui-text); text-align: left; cursor: pointer; }
.space-nav__item:hover { background: var(--ui-surface-muted); }
.space-nav__item.active { background: var(--ui-primary-soft); }
.space-nav__glyph { width: 2.35rem; height: 2.35rem; display: grid; place-items: center; border-radius: .8rem; background: var(--ui-surface-muted); color: var(--ui-text-muted); }
.space-nav__item.active .space-nav__glyph { background: var(--ui-surface); color: var(--ui-primary); }
.space-nav__copy { min-width: 0; display: grid; gap: .15rem; }
.space-nav__copy strong, .space-nav__copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.space-nav__copy strong { font-size: var(--ui-text-sm); }
.space-nav__copy small { color: var(--ui-text-subtle); font-size: var(--ui-text-xs); }
.space-nav__chevron { color: var(--ui-text-subtle); font-size: .72rem; }
.space-nav__empty { min-height: 12rem; display: grid; place-items: center; align-content: center; gap: var(--ui-space-2); padding: var(--ui-space-4); text-align: center; color: var(--ui-text-muted); }
.space-nav__empty > i { width: 2.8rem; height: 2.8rem; display: grid; place-items: center; border-radius: 1rem; background: var(--ui-surface-muted); color: var(--ui-text-subtle); }
.space-nav__empty strong { color: var(--ui-text); font-size: var(--ui-text-sm); }
.space-nav__empty span { font-size: var(--ui-text-xs); line-height: 1.45; }
.space-nav__footer { padding: var(--ui-space-3); border-top: 1px solid var(--ui-border); }
.space-nav__footer .ui-button { width: 100%; }
@media (max-width: 900px) {
	.space-nav { position: absolute; inset: 0 auto 0 0; z-index: 40; width: min(22rem, 88vw); transform: translateX(-105%); box-shadow: var(--ui-shadow-lg); transition: transform var(--ui-motion-normal) var(--ui-ease); }
	.space-nav.active { transform: translateX(0); }
	.space-nav__close { display: grid !important; }
}
</style>
