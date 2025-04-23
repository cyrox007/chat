<template>
	<aside class="admin-sidebar">
		<nav>
			<router-link :to="{ name: 'AdminDashboardHome' }" class="sidebar-link" active-class="active">
				<i class="fas fa-tachometer-alt"></i>
				<span>Консоль</span>
			</router-link>
			<router-link :to="{ name: 'AdminProfileList' }" class="sidebar-link" active-class="active">
				<i class="fas fa-users"></i>
				<span>Пользователи</span>
			</router-link>
		</nav>
	</aside>
</template>

<script setup>
import { computed } from 'vue';
import { useStore } from 'vuex';
const store = useStore();
const userRole = computed(() => store.getters['getUser'].global_role);
</script>

<style scoped>
.admin-sidebar {
	width: 250px;
	background-color: var(--sidebar-bg-light);
	border-right: 1px solid var(--messenger-border);
	padding: 20px 0;
}

.sidebar-link {
	display: flex;
	align-items: center;
	padding: 12px 20px;
	color: var(--text-light);
	text-decoration: none;
	transition: all 0.3s;
}

.sidebar-link:hover {
	background-color: var(--primary-color-hover);
	color: white;
}

.sidebar-link.active {
	background-color: var(--primary-color);
	color: white;
}

.sidebar-link i {
	margin-right: 10px;
	width: 20px;
	text-align: center;
}
</style>