<template>
	<div v-if="showDeleteModal" class="delete-modal">
		<div class="modal-content">
			<h3>Подтвердите удаление</h3>
			<p>Вы уверены, что хотите удалить пользователя? Это действие необратимо.</p>
			<div class="modal-actions">
				<button @click="confirmDelete">Удалить</button>
				<button @click="cancelDelete">Отмена</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, defineExpose } from 'vue';
import UsersServices from '@/API/UsersService';

// Состояние модального окна
const showDeleteModal = ref(false);

// Открытие модального окна
const openDeleteModal = () => {
	showDeleteModal.value = true;
};

// Подтверждение удаления
const confirmDelete = async () => {
	try {
		await UsersServices.delete_user(user.value.uid);
		alert('Пользователь успешно удален.');
		window.location.href = '/'; // Перенаправление на главную страницу
	} catch (error) {
		console.error('Ошибка при удалении пользователя:', error);
	}
};

// Отмена удаления
const cancelDelete = () => {
	showDeleteModal.value = false;
};

// Экспорт методов
defineExpose({
	openDeleteModal,
});
</script>

<style scoped>
.delete-modal {
	position: fixed;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	background: rgba(0, 0, 0, 0.5);
	display: flex;
	justify-content: center;
	align-items: center;
}

.modal-content {
	background: white;
	padding: 20px;
	border-radius: 8px;
	text-align: center;
}

.modal-actions button {
	margin: 0 10px;
}
</style>