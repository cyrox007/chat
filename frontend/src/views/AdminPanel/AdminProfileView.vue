<template>
	<div class="admin-profile">
	  <h1>Админ-панель: Редактирование профиля</h1>
	  <form @submit.prevent="saveChanges">
		<div class="form-group">
		  <label for="status">Статус:</label>
		  <select id="status" v-model="profile.status">
			<option value="active">Активен</option>
			<option value="inactive">Неактивен</option>
			<option value="deleted">Удален</option>
		  </select>
		</div>
		<div class="form-group">
		  <label for="role">Роль:</label>
		  <select id="role" v-model="profile.role">
			<option value="user">Пользователь</option>
			<option value="moderator">Модератор</option>
			<option value="admin">Администратор</option>
		  </select>
		</div>
		<div class="form-actions">
		  <button type="submit">Сохранить изменения</button>
		  <button type="button" @click="deleteProfile">Удалить профиль</button>
		</div>
	  </form>
	</div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import { useRoute, useRouter } from "vue-router";
  import UsersServices from "@/API/UsersService";
  
  const route = useRoute();
  const router = useRouter();
  
  const profile = ref({
	status: "active",
	role: "user",
  });
  
  const saveChanges = async () => {
	try {
	  await UsersServices.updateAdminProfile(route.params.uid, profile.value);
	  alert("Изменения сохранены");
	} catch (error) {
	  console.error("Ошибка при сохранении изменений:", error);
	}
  };
  
  const deleteProfile = async () => {
	if (confirm("Вы уверены, что хотите удалить профиль?")) {
	  try {
		await UsersServices.deleteProfile(route.params.uid);
		alert("Профиль удален");
		router.push("/admin");
	  } catch (error) {
		console.error("Ошибка при удалении профиля:", error);
	  }
	}
  };
  </script>
  
  <style scoped>
  .admin-profile {
	max-width: 600px;
	margin: 0 auto;
	padding: 20px;
	background: var(--bg-light);
	box-shadow: var(--shadow-light);
	border-radius: 8px;
  }
  </style>