<template>
	<div class="moderation-modal" :class="props.showModal ? 'active' : ''">
		<div class="modal-content">
			<h2>Назначить наказание</h2>
			<form @submit.prevent="handleSubmit">
				<div class="form-group">
					<label for="type">Тип наказания:</label>
					<select id="type" v-model="punishment.type">
						<option value="mute">Запрет писать в чате</option>
						<!-- <option value="room_ban">Запрет писать в месенджере</option> -->
					</select>
				</div>
				<div class="form-group">
					<label for="endDateTime">Дата и время окончания наказания:</label>
					<input type="datetime-local" id="endDateTime" v-model="punishment.endDateTime" required />
				</div>
				<div class="form-group">
					<label for="reason">Причина:</label>
					<textarea id="reason" v-model="punishment.reason" class="no-resize"></textarea>
				</div>
				<div class="form-actions">
					<button type="submit" :disabled="isSubmitting">
                        {{ isSubmitting ? 'Отправка...' : 'Назначить' }}
                    </button>
					<button type="button" @click="closeModerationModal">Отмена</button>
				</div>
			</form>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue';

import PenaltyService from '@/API/PenaltyService';

const isSubmitting = ref(false);

const props = defineProps({
	showModal: {
		type: Boolean,
		required: true,
		default: false,
	},
	userUid: {
        type: String,
        required: true,
    }
});

const emit = defineEmits(['close']);

// Функция для получения текущего времени +30 минут
const getDefaultEndDateTime = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 30); // Добавляем 30 минут

    // Форматируем дату в локальном часовом поясе
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0'); // Месяцы начинаются с 0
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day}T${hours}:${minutes}`; // Локальное время в формате YYYY-MM-DDTHH:mm
};

const punishment = ref({
	type: "mute",
	endDateTime: getDefaultEndDateTime(), // Устанавливаем значение по умолчанию
	reason: "",
});

const handleSubmit = async () => {
	try {
		isSubmitting.value = true; // Включаем индикатор загрузки

		// Преобразуем локальное время в UTC перед отправкой
		const localDate = new Date(punishment.value.endDateTime);
		const utcDate = localDate.toISOString().replace('Z', '+00:00'); // Преобразование в UTC

		// Формируем данные для отправки
		const payload = {
			type: punishment.value.type,
			end_time_utc: utcDate, // Время окончания в UTC
			reason: punishment.value.reason,
		};

		// Отправляем данные на сервер
		await PenaltyService.assignPenalty(props.userUid, payload);

		alert("Наказание успешно назначено");
		closeModerationModal();
	} catch (error) {
		console.error("Ошибка при назначении наказания:", error);
		alert("Не удалось назначить наказание. Попробуйте позже.");
	} finally {
		isSubmitting.value = false; // Выключаем индикатор загрузки
	}
};

const closeModerationModal = () => {
	emit('close');
};
</script>

<style scoped>
.moderation-modal {
	position: relative;
	top: 0;
	left: 0;
	bottom: 0;
	right: 0;
	width: 0;
	height: 0;
	background: rgba(0, 0, 0, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	opacity: 0;
	transition: opacity .4s ease-in-out;
	overflow: hidden;
	z-index: 9999;
}

.moderation-modal.active {
	position: fixed;
	height: auto;
	width: auto;
	opacity: 1;
}

.modal-content {
	background: var(--bg-light);
	padding: 20px;
	border-radius: 8px;
	width: 400px;
}
.no-resize {
  resize: none; /* Запрещаем изменение размера */
}
</style>