import { useStore } from 'vuex';

export function hasAccess(allowedRoles, options = {}) {
	const store = useStore();
	const userRole = store.getters['getUser'].global_role || 'guest'; // Получаем роль из хранилища

	const { requireAll = false } = options;

	if (!allowedRoles || allowedRoles.length === 0) {
		return false;
	}

	if (requireAll) {
		// Проверяем, что у пользователя есть все требуемые роли
		return allowedRoles.every(role => userRole === role);
	}

	// Проверяем, что у пользователя есть хотя бы одна из требуемых ролей
	return allowedRoles.includes(userRole);
}