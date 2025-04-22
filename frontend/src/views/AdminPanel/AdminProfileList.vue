<template>
	<div class="admin-profile-list">
		<div class="admin-toolbar">
			<h2>Управление пользователями</h2>

			<div class="controls">
				<div class="search-box">
					<input v-model="searchQuery" type="text" placeholder="Поиск пользователей..."
						@input="handleSearch" />
					<i class="fas fa-search"></i>
				</div>

				<button class="btn-refresh" @click="fetchUsers">
					<i class="fas fa-sync-alt"></i>
				</button>
			</div>
		</div>

		<div class="user-table-container">
			<table class="user-table">
				<thead>
					<tr>
						<th @click="sortBy('id')">
							UUID
							<i :class="sortIcon('id')"></i>
						</th>
						<th @click="sortBy('username')">
							Логин
							<i :class="sortIcon('username')"></i>
						</th>
						<th @click="sortBy('email')">
							Email
							<i :class="sortIcon('email')"></i>
						</th>
						<th @click="sortBy('created_at')">
							Дата регистрации
							<i :class="sortIcon('created_at')"></i>
						</th>
						<th @click="sortBy('role')">
							Роль
							<i :class="sortIcon('role')"></i>
						</th>
						<th>Действия</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="user in users" :key="user.id">
						<td>{{ user.uid }}</td>
						<td>{{ user.username }}</td>
						<td>{{ user.email }}</td>
						<td>{{ formatDate(user.created_at) }}</td>
						<td>
							<span :class="`role-badge ${user.role}`">
								{{ userRoleNames[user.global_role] || user.global_role }}
							</span>
						</td>
						<td class="actions">
							<button class="btn-edit" @click="editUser(user)" title="Редактировать">
								<i class="fas fa-edit"></i>
							</button>
							<!-- <button class="btn-ban" @click="toggleBanUser(user)"
								:title="user.is_banned ? 'Разблокировать' : 'Заблокировать'">
								<i :class="user.is_banned ? 'fas fa-unlock' : 'fas fa-ban'"></i>
							</button> -->
						</td>
					</tr>
					<tr v-if="users.length === 0">
						<td colspan="6" class="no-results">
							Пользователи не найдены
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<div class="pagination-container">
			<div class="pagination-info">
				Показано {{ showingFrom }}-{{ showingTo }} из {{ totalUsers }}
			</div>
			<div class="pagination-controls">
				<button class="pagination-btn" @click="prevPage" :disabled="currentPage === 1">
					<i class="fas fa-chevron-left"></i>
				</button>

				<button v-for="page in visiblePages" :key="page" class="pagination-btn"
					:class="{ active: page === currentPage }" @click="goToPage(page)">
					{{ page }}
				</button>

				<button class="pagination-btn" @click="nextPage" :disabled="currentPage === totalPages">
					<i class="fas fa-chevron-right"></i>
				</button>
			</div>
			<div class="page-size-selector">
				<select v-model="perPage" @change="handlePageSizeChange">
					<option value="10">10 на странице</option>
					<option value="25">25 на странице</option>
					<option value="50">50 на странице</option>
					<option value="100">100 на странице</option>
				</select>
			</div>
		</div>

		<!-- Модальное окно редактирования -->
		<!-- <UserEditModal v-if="editingUser" :user="editingUser" @close="closeEditModal" @save="saveUserChanges" /> -->
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useStore } from 'vuex';

import ProfileService from '@/API/Admin/ProfileService';
import router from '@/router';

const store = useStore();

// Состояния
const users = ref([]);
const searchQuery = ref('');
const currentPage = ref(1);
const perPage = ref(10);
const totalUsers = ref(0);
const sortField = ref('created_at');
const sortDirection = ref('desc');
const editingUser = ref(null);

// Названия ролей для отображения
const userRoleNames = {
	user: 'Пользователь',
	moderator: 'Модератор',
	admin: 'Администратор',
	superadmin: 'Супер-админ'
};

// Получение данных
const fetchUsers = async () => {
	try {
		const params = {
			page: currentPage.value,
			per_page: perPage.value,
			search: searchQuery.value,
			sort_by: sortField.value,
			sort_dir: sortDirection.value
		};

		const response = await ProfileService.getUsers(params);
		users.value = response.data;
		totalUsers.value = response.total;
	} catch (error) {
		console.error('Ошибка загрузки пользователей:', error);
		alert('Не удалось загрузить список пользователей');
	}
};

// Поиск с задержкой
let searchTimeout = null;
const handleSearch = () => {
	clearTimeout(searchTimeout);
	searchTimeout = setTimeout(() => {
		currentPage.value = 1;
		fetchUsers();
	}, 500);
};

// Сортировка
const sortBy = (field) => {
	if (sortField.value === field) {
		sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
	} else {
		sortField.value = field;
		sortDirection.value = 'asc';
	}
	fetchUsers();
};

const sortIcon = (field) => {
	if (sortField.value !== field) return 'fas fa-sort';
	return sortDirection.value === 'asc'
		? 'fas fa-sort-up'
		: 'fas fa-sort-down';
};

// Пагинация
const totalPages = computed(() => Math.ceil(totalUsers.value / perPage.value));
const showingFrom = computed(() => (currentPage.value - 1) * perPage.value + 1);
const showingTo = computed(() => Math.min(currentPage.value * perPage.value, totalUsers.value));

const visiblePages = computed(() => {
	const pages = [];
	const maxVisible = 5;
	let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2));
	let end = Math.min(totalPages.value, start + maxVisible - 1);

	if (end - start + 1 < maxVisible) {
		start = Math.max(1, end - maxVisible + 1);
	}

	for (let i = start; i <= end; i++) {
		pages.push(i);
	}

	return pages;
});

const goToPage = (page) => {
	if (page !== currentPage.value) {
		currentPage.value = page;
		fetchUsers();
	}
};

const prevPage = () => {
	if (currentPage.value > 1) {
		currentPage.value--;
		fetchUsers();
	}
};

const nextPage = () => {
	if (currentPage.value < totalPages.value) {
		currentPage.value++;
		fetchUsers();
	}
};

const handlePageSizeChange = () => {
	currentPage.value = 1;
	fetchUsers();
};

// Форматирование даты
const formatDate = (dateString) => {
	return new Date(dateString).toLocaleDateString('ru-RU', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
};

// Работа с пользователями
const editUser = (user) => {
	router.push(`/admin/profile/${user.uid}`)
};

const closeEditModal = () => {
	editingUser.value = null;
};

/* const saveUserChanges = async (updatedUser) => {
	try {
		await store.dispatch('admin/updateUser', updatedUser);
		fetchUsers();
		closeEditModal();
	} catch (error) {
		console.error('Ошибка обновления пользователя:', error);
		alert('Не удалось обновить данные пользователя');
	}
}; */

const toggleBanUser = async (user) => {
	if (confirm(`Вы уверены, что хотите ${user.is_banned ? 'разблокировать' : 'заблокировать'} пользователя ${user.username}?`)) {
		try {
			await store.dispatch('admin/toggleBanUser', user.id);
			fetchUsers();
		} catch (error) {
			console.error('Ошибка блокировки пользователя:', error);
			alert('Не удалось изменить статус блокировки');
		}
	}
};

// Инициализация
onMounted(() => {
	fetchUsers();
});
</script>

<style scoped>
.admin-profile-list {
	padding: 20px;
	background-color: var(--bg-light);
	border-radius: 8px;
	box-shadow: var(--shadow-light);
}

.admin-toolbar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 20px;
	flex-wrap: wrap;
	gap: 15px;
}

.controls {
	display: flex;
	align-items: center;
	gap: 10px;
}

.search-box {
	position: relative;
}

.search-box input {
	padding: 8px 30px 8px 10px;
	border: 1px solid var(--messenger-border);
	border-radius: 4px;
	width: 250px;
}

.search-box i {
	position: absolute;
	right: 10px;
	top: 50%;
	transform: translateY(-50%);
	color: var(--primary-color);
}

.btn-refresh {
	background: none;
	border: none;
	cursor: pointer;
	color: var(--primary-color);
	font-size: 16px;
	padding: 5px;
}

.user-table-container {
	overflow-x: auto;
	margin-bottom: 20px;
}

.user-table {
	width: 100%;
	border-collapse: collapse;
	background-color: var(--bg-light);
}

.user-table th,
.user-table td {
	padding: 12px 15px;
	text-align: left;
	border-bottom: 1px solid var(--messenger-border);
}

.user-table th {
	background-color: var(--sidebar-bg-light);
	font-weight: 600;
	cursor: pointer;
	user-select: none;
}

.user-table th:hover {
	background-color: var(--primary-color-hover);
	color: white;
}

.user-table tr:hover td {
	background-color: rgba(var(--primary-color-rgb), 0.1);
}

.role-badge {
	display: inline-block;
	padding: 3px 8px;
	border-radius: 12px;
	font-size: 12px;
	font-weight: 500;
}

.role-badge.user {
	background-color: #e1f5fe;
	color: #0288d1;
}

.role-badge.moderator {
	background-color: #e8f5e9;
	color: #388e3c;
}

.role-badge.admin {
	background-color: #f3e5f5;
	color: #8e24aa;
}

.role-badge.superadmin {
	background-color: #fff3e0;
	color: #e65100;
}

.actions {
	display: flex;
	gap: 5px;
}

.btn-edit,
.btn-ban {
	background: none;
	border: none;
	cursor: pointer;
	padding: 5px;
	border-radius: 4px;
}

.btn-edit {
	color: var(--primary-color);
}

.btn-edit:hover {
	background-color: rgba(var(--primary-color-rgb), 0.1);
}

.btn-ban {
	color: #f44336;
}

.btn-ban:hover {
	background-color: rgba(244, 67, 54, 0.1);
}

.no-results {
	text-align: center;
	padding: 20px;
	color: #666;
}

.pagination-container {
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: 15px;
	margin-top: 20px;
}

.pagination-controls {
	display: flex;
	gap: 5px;
}

.pagination-btn {
	padding: 5px 10px;
	border: 1px solid var(--messenger-border);
	background: none;
	cursor: pointer;
	border-radius: 4px;
	min-width: 32px;
}

.pagination-btn:hover:not(:disabled) {
	background-color: var(--primary-color-hover);
	color: white;
}

.pagination-btn.active {
	background-color: var(--primary-color);
	color: white;
	border-color: var(--primary-color);
}

.pagination-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.page-size-selector select {
	padding: 5px;
	border: 1px solid var(--messenger-border);
	border-radius: 4px;
	background-color: var(--bg-light);
	color: var(--text-light);
}

@media (max-width: 768px) {
	.admin-toolbar {
		flex-direction: column;
		align-items: flex-start;
	}

	.search-box input {
		width: 100%;
	}

	.pagination-container {
		flex-direction: column;
		align-items: center;
	}

	.user-table th,
	.user-table td {
		padding: 8px 10px;
		font-size: 14px;
	}
}
</style>