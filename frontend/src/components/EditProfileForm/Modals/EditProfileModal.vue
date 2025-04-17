<template>
	<div class="edit-profile" :class="props.modalShow ? 'active' : ''">
		<div class="edit-profile-form">
			<h2>Редактирование профиля</h2>
			<form @submit.prevent="saveProfile">
				<!-- Форма редактирования -->
				<div class="form-group">
					<label for="first_name">Имя:</label>
					<input type="text" id="first_name" v-model="profile.first_name" />
				</div>
				<div class="form-group">
					<label for="last_name">Фамилия:</label>
					<input type="text" id="last_name" v-model="profile.last_name" />
				</div>
				<div class="form-group">
					<label for="email">Email:</label>
					<input type="email" id="email" v-model="profile.email" required disabled />
				</div>
				<div class="form-group">
					<label for="phone">Телефон:</label>
					<input type="text" id="phone" v-model="profile.phone" disabled />
				</div>
				<div class="form-group">
					<label for="country">Страна:</label>
					<select id="country" v-model="selectedCountry" @change="filterCities">
						<option value="">Выберите страну</option>
						<option v-for="country in countries" :key="country" :value="country">{{ country }}</option>
					</select>
				</div>
				<div class="form-group">
					<label for="city">Город:</label>
					<input type="text" id="city" v-model="cityInput" list="city-list" />
					<datalist id="city-list">
						<option v-for="city in filteredCities" :key="city" :value="city">{{ city }}</option>
					</datalist>
				</div>
				<div class="form-group">
					<label for="bio">Биография:</label>
					<textarea id="bio" v-model="profile.bio"></textarea>
				</div>
				
				
				<div class="form-actions">
					<button type="submit" @click="">Сохранить изменения</button>
					<button type="button" @click="cancelEdit">Отмена</button>
				</div>
			</form>
			<hr>
			<!-- Кнопка удаления профиля -->
			<div class="form-group" style="display: flex; align-items: center; justify-content: space-between;">
				<label for="delete-profile" style="margin: 0;">Удаление профиля:</label>
				<button v-if="canDeleteProfile" @click="toggleDeleteConfirmationModal" class="delete-profile-btn" style="margin: 0;">Удалить
					профиль</button>
			</div>
			<hr>
			<!-- Модальное окно удаления -->
			<DeleteConfirmationModal :modalShow="isDeleteConfirmationModalOpen" @close="toggleDeleteConfirmationModal"
				@confirm="handleProfileDeletion" />
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watchEffect } from "vue";
import { useStore } from "vuex";
import UsersServices from "@/API/UsersService";
import DeleteConfirmationModal from "@/components/EditProfileForm/Modals/DeleteConfirmationModal.vue";
import CSRFService from "@/API/CSRFService";

const props = defineProps({
	modalShow: {
		type: Boolean,
		required: true,
		default: false
	},
	user: {
		type: Object,
		required: true,
		default: () => ({}), // По умолчанию пустой объект
	},
});

const emits = defineEmits(['close', 'save']);
const store = useStore();

const isDeleteConfirmationModalOpen = ref(false);
const profile = ref({...props.user});
const selectedCountry = ref(props.user?.country || '');
const cityInput = ref(props.user?.city || '');
const countries = ['Россия', 'Белоруссия']; // Пример списка стран
const cities = {
	Россия: ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань', 'Красноярск', 'Нижний Новгород', 'Челябинск', 'Уфа', 'Самара'],
	Белоруссия: ['Минск', 'Гомель', 'Могилёв', 'Витебск', 'Гродно', 'Брест', 'Бобруйск', 'Барановичи', 'Борисов', 'Пинск'],
};

const currentUser = computed(() => store.getters.getUser);

const filteredCities = computed(() => {
	return selectedCountry.value ? cities[selectedCountry.value] || [] : [];
});

const canDeleteProfile = computed(() => {
	return currentUser.value; // Только текущий пользователь может удалять свой профиль
});

const toggleDeleteConfirmationModal = () => {
	isDeleteConfirmationModalOpen.value = !isDeleteConfirmationModalOpen.value;
};

const handleProfileDeletion = async () => {
	try {
		const response = await UsersServices.deleteProfile(currentUser.value.uid);
		if (response.data.status === 'ok') {
			await store.dispatch('logout');
		} else {
			console.error('Ошибка при удалении профиля:', response.data.message);
		}
	} catch (error) {
		console.error('Ошибка при удалении профиля:', error);
	}
};

const cancelEdit = () => {
	emits('close');
}
const saveProfile = async () => {

	// Подготовка данных для отправки
	const updatedData = {
        first_name: profile.value.first_name || '',
        last_name: profile.value.last_name || '',
        email: profile.value.email || '',
        phone: profile.value.phone || '',
        country: selectedCountry.value || '',
        city: cityInput.value || '',
        bio: profile.value.bio || '',
    };

    // Проверка, что есть данные для отправки
    if (!Object.values(updatedData).some(value => value)) {
        console.error('Нет данных для обновления профиля');
        return;
    }
	emits('save', updatedData);
};

watchEffect(() => {
    profile.value = { ...props.user };
    selectedCountry.value = props.user?.country || '';
    cityInput.value = props.user?.city || '';
});
</script>

<style>
.edit-profile {
	position: relative;
	z-index: 9999;
	top: 0;
	bottom: 0;
	left: 0; right: 0;
	width: 0;
	height: 0;
	background: rgba(94, 94, 94, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	opacity: 0;
	transition: opacity .4s ease-in-out;
	overflow: hidden;
}
.edit-profile.active {
	position: fixed;
	height: auto;
	width: auto;
	opacity: 1;
}

.edit-profile-form {
	max-width: 600px;
	margin: 20px auto;
	padding: 20px;
	background: var(--bg-light);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	border-radius: 8px;
}

.form-group {
	margin-bottom: 15px;
}

label {
	display: block;
	font-weight: bold;
	margin-bottom: 5px;
}

input,
select,
textarea {
	width: 100%;
	padding: 8px;
	border: 1px solid #ccc;
	border-radius: 4px;
}

button {
	padding: 8px 16px;
	background: var(--profile-edit-btn);
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
	margin-right: 10px;
}

button:hover {
	background: var(--profile-edit-btn-hover);
}

.delete-profile-btn {
	background: red;
	color: white;
	border: none;
	padding: 8px 16px;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.3s ease;
	margin-top: 10px;
}

.delete-profile-btn:hover {
	background: darkred;
}
</style>