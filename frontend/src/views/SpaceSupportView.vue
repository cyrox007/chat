<template>
	<main class="support-page">
		<header class="support-hero" v-if="space">
			<div>
				<RouterLink :to="{ name: 'space', params: { uid: space.uid } }" class="back-link"><i class="fas fa-arrow-left"></i>В разговор</RouterLink>
				<span class="eyebrow">Поддержка пространства</span>
				<h1>{{ space.name }}</h1>
				<p>Здесь можно оставить бесплатный cosmetic gift как знак благодарности. Поддержка не покупает права, рейтинг или влияние.</p>
			</div>
			<RouterLink class="ui-button ui-button--ghost" :to="{ name: 'space-life', params: { uid: space.uid } }">Жизнь пространства</RouterLink>
		</header>

		<section v-if="loading" class="state-card">Загружаем поддержку…</section>
		<section v-else-if="errorMessage" class="state-card state-card--error">{{ errorMessage }}</section>
		<SpaceSupportPanel
			v-else-if="space"
			:space-uid="space.uid"
			:can-manage="Boolean(space.can_manage)"
			:is-active-member="isActiveMember"
			:is-owner="isOwner"
		/>
	</main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import SpacesService from '@/API/SpacesService';
import SpaceSupportPanel from '@/components/Spaces/SpaceSupportPanel.vue';

const route = useRoute();
const loading = ref(true);
const errorMessage = ref('');
const space = ref(null);
const spaceUid = computed(() => String(route.params.uid || ''));
const isOwner = computed(() => Boolean(space.value?.viewer_membership?.role === 'owner' || space.value?.owner_uid === space.value?.viewer_membership?.account_uid));
const isActiveMember = computed(() => Boolean(space.value?.viewer_membership?.status === 'active' || space.value?.can_manage));

const load = async () => {
	loading.value = true; errorMessage.value = '';
	try {
		const response = await SpacesService.get(spaceUid.value);
		space.value = response.data.space;
	} catch { space.value = null; errorMessage.value = 'Пространство недоступно.'; }
	finally { loading.value = false; }
};

watch(spaceUid, load);
onMounted(load);
</script>

<style scoped>
.support-page{display:grid;gap:var(--ui-space-5);padding-bottom:var(--ui-space-8)}.support-hero{display:flex;align-items:flex-end;justify-content:space-between;gap:var(--ui-space-5);padding:clamp(1.4rem,4vw,2.4rem);border:1px solid var(--ui-border);border-radius:var(--ui-radius-xl);background:linear-gradient(135deg,var(--ui-surface),var(--ui-primary-soft))}.support-hero>div{max-width:44rem}.back-link{display:inline-flex;align-items:center;gap:.45rem;margin-bottom:var(--ui-space-4);color:var(--ui-text-muted);text-decoration:none}.eyebrow{display:block;color:var(--ui-primary);font-size:var(--ui-text-xs);font-weight:800;letter-spacing:.08em;text-transform:uppercase}.support-hero h1{margin:.3rem 0 0;font-size:clamp(1.8rem,4vw,2.8rem)}.support-hero p{margin:var(--ui-space-3) 0 0;color:var(--ui-text-muted);line-height:1.6}.state-card{min-height:12rem;display:grid;place-items:center;padding:var(--ui-space-6);border:1px dashed var(--ui-border);border-radius:var(--ui-radius-xl);color:var(--ui-text-muted)}.state-card--error{border-color:color-mix(in srgb,var(--ui-danger) 35%,var(--ui-border));color:var(--ui-danger)}@media(max-width:680px){.support-hero{align-items:stretch;flex-direction:column}.support-hero .ui-button{width:100%}}
</style>
