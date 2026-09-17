<template>
	<div class="message" :class="{ sent: message.isCurrentUser, received: !message.isCurrentUser }"
		:data-message-id="message.uid" :data-is-current-user="message.isCurrentUser" :data-is-read="message.is_read">
		<div v-if="message.reply_to" class="reply-preview">
			<div class="reply-header">
				<i class="fas fa-reply"></i> {{ message.reply_to.sender.name }}
				<span class="reply-time">{{ replyTime }}</span>
			</div>
			<div class="reply-content">{{ truncate(message.reply_to.content, 50) }}</div>
		</div>

		<div class="message-body">
			<div v-if="message.content_type === 'text'">{{ message.content }}</div>

			<div v-else-if="message.content_type === 'image'" class="image-list">
				<div v-for="(image, index) in message.media_metadata.files" :key="index" class="image-item">
					<img :src="apiBaseUrl + image.url" alt="Изображение" class="message-image" />
				</div>
			</div>

			<div v-else-if="message.content_type === 'video'" class="video-container">
				<video controls class="message-video">
					<source :src="apiBaseUrl + message.media_metadata.files[0].url" type="video/mp4" />
					Ваш браузер не поддерживает видео.
				</video>
			</div>

			<div v-else-if="message.content_type === 'audio'" class="audio-container">
				<audio controls class="message-audio">
					<source :src="apiBaseUrl + message.media_metadata.files[0].url" type="audio/mpeg" />
					Ваш браузер не поддерживает аудио.
				</audio>
			</div>

			<div v-else-if="message.content_type === 'voice'" class="audio-container">
				<audio controls class="message-audio">
					<source :src="apiBaseUrl + message.media_metadata.voice" />
				</audio>
			</div>

			<div v-else-if="message.content_type === 'file'" class="file-list">
				<div v-for="(file, index) in message.media_metadata.files" :key="index" class="file-item">
					<span v-if="isImage(file)" class="file-thumbnail">
						<img :src="apiBaseUrl + file.url" alt="Thumbnail" />
					</span>
					<span v-else class="file-icon">
						<i :class="getFileIcon(file.name)"></i>
					</span>
					<a :href="apiBaseUrl + file.url" target="_blank" rel="noopener" class="file-link">{{ file.name }}</a>
				</div>
			</div>

			<div v-else>Неизвестный тип сообщения</div>
		</div>

		<div class="message-meta">
			<span class="message-time">{{ formatTime(message.created_at) }}</span>
			<button v-if="!message.isCurrentUser && message.uid && !reportSent" class="report-toggle" type="button" :aria-expanded="reportOpen" @click="reportOpen = !reportOpen">
				<i class="far fa-flag" aria-hidden="true"></i><span>Пожаловаться</span>
			</button>
			<span v-if="reportSent" class="report-sent"><i class="fas fa-check"></i> Жалоба отправлена</span>
		</div>

		<form v-if="reportOpen && !reportSent" class="report-form" @submit.prevent="submitReport">
			<label>Причина
				<select v-model="reportCategory">
					<option value="spam">Спам</option>
					<option value="harassment">Преследование / оскорбления</option>
					<option value="sexual">Сексуальный контент</option>
					<option value="violence">Угрозы / насилие</option>
					<option value="privacy">Нарушение приватности</option>
					<option value="impersonation">Выдаёт себя за другого</option>
					<option value="fraud">Мошенничество</option>
					<option value="hate">Травля по признаку группы</option>
					<option value="self_harm">Риск самоповреждения</option>
					<option value="minor_safety">Безопасность несовершеннолетних</option>
					<option value="other">Другое</option>
				</select>
			</label>
			<label>Комментарий <span>необязательно</span>
				<textarea v-model.trim="reportDescription" rows="2" maxlength="2000" placeholder="Коротко опишите проблему. Не добавляйте лишние персональные данные."></textarea>
			</label>
			<p class="report-privacy">Команда Trust & Safety получит это конкретное сообщение. Полная история личного диалога автоматически не открывается.</p>
			<p v-if="reportError" class="report-error" role="alert">{{ reportError }}</p>
			<div class="report-actions"><button type="button" :disabled="reportSubmitting" @click="reportOpen = false">Отмена</button><button class="ui-button" type="submit" :disabled="reportSubmitting">{{ reportSubmitting ? 'Отправляем…' : 'Отправить' }}</button></div>
		</form>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue';

import ModerationService from '@/API/ModerationService';
import { formatUTCDate } from '@/utils/dateFormatter';

const props = defineProps({
	message: {
		type: Object,
		required: true,
	},
});

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const reportOpen = ref(false);
const reportSubmitting = ref(false);
const reportSent = ref(false);
const reportError = ref('');
const reportCategory = ref('harassment');
const reportDescription = ref('');

const truncate = (text, length) => {
	const value = String(text || '');
	return value.length > length ? `${value.substring(0, length)}...` : value;
};

const isImage = (file) => {
	const imageExtensions = ['jpg', 'jpeg', 'png', 'gif'];
	const extension = String(file?.name || '').split('.').pop().toLowerCase();
	return imageExtensions.includes(extension);
};

const getFileIcon = (fileName) => {
	const extension = String(fileName || '').split('.').pop().toLowerCase();
	switch (extension) {
		case 'pdf': return 'fas fa-file-pdf';
		case 'doc':
		case 'docx': return 'fas fa-file-word';
		case 'xls':
		case 'xlsx': return 'fas fa-file-excel';
		default: return 'fas fa-file';
	}
};

const submitReport = async () => {
	if (!props.message.uid || props.message.isCurrentUser) return;
	reportSubmitting.value = true;
	reportError.value = '';
	try {
		await ModerationService.createTrustSafetyReport({
			source_type: 'messenger_message',
			source_uid: props.message.uid,
			category: reportCategory.value,
			description: reportDescription.value || null,
		});
		reportSent.value = true;
		reportOpen.value = false;
	} catch (error) {
		const type = error.response?.data?.detail?.error_type;
		reportError.value = type === 'trust_safety_report_rate_limited'
			? 'Слишком много новых жалоб за короткое время. Попробуйте позже.'
			: 'Не удалось отправить жалобу. Попробуйте ещё раз.';
	} finally {
		reportSubmitting.value = false;
	}
};

const formatTime = (dateString) => formatUTCDate(dateString, { showSeconds: false, showDate: false });
const replyTime = computed(() => {
	if (!props.message.reply_to) return '';
	return formatUTCDate(props.message.reply_to.created_at, { showSeconds: false, showDate: true });
});
</script>

<style scoped>
.message{margin-bottom:15px;max-width:70%}.message.sent{margin-left:auto;text-align:right}.message.received{margin-right:auto}.message-body{padding:10px 15px;border-radius:18px;display:inline-block;text-align:left}.message.sent .message-body{background-color:var(--primary-color);color:white}.message.received .message-body{background-color:var(--other-user-bg);color:var(--text-light)}.message-meta{display:flex;align-items:center;gap:.5rem;margin-top:5px}.message.sent .message-meta{justify-content:flex-end}.message-time{font-size:.7em;color:var(--ui-text-subtle,#777)}.report-toggle{display:inline-flex;align-items:center;gap:.25rem;padding:.15rem .35rem;border:0;background:transparent;color:var(--ui-text-subtle,#777);font-size:.68rem;cursor:pointer}.report-toggle:hover,.report-toggle:focus-visible{color:var(--ui-danger,#b42318)}.report-sent{font-size:.68rem;color:var(--ui-success,#15803d)}.report-form{display:grid;gap:.6rem;margin-top:.5rem;padding:.75rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-md);background:var(--ui-surface);color:var(--ui-text);text-align:left}.report-form label{display:grid;gap:.3rem;font-size:.75rem;font-weight:700}.report-form label span{font-weight:400;color:var(--ui-text-subtle)}.report-form select,.report-form textarea{width:100%;padding:.5rem .6rem;border:1px solid var(--ui-border);border-radius:var(--ui-radius-sm);background:var(--ui-surface);color:var(--ui-text);font:inherit}.report-privacy{margin:0;color:var(--ui-text-muted);font-size:.7rem;line-height:1.4}.report-error{margin:0;color:var(--ui-danger);font-size:.72rem}.report-actions{display:flex;justify-content:flex-end;gap:.45rem}.report-actions>button:not(.ui-button){border:0;background:transparent;color:var(--ui-text-muted);cursor:pointer}.reply-preview{margin-bottom:10px;padding:8px;background-color:#e0e0e0;border-radius:8px}.reply-header{font-size:12px;color:#555}.reply-content{font-size:14px;color:#333}.image-list{display:flex;gap:10px}.image-item img{max-width:450px;height:auto;border-radius:8px}.video-container video{max-width:100%;height:auto}.audio-container audio{width:100%}.file-list .file-item{display:flex;align-items:center;margin-bottom:5px}.file-icon i{font-size:24px;margin-right:10px}.file-link{text-decoration:none;color:var(--primary-color)}
@media(max-width:680px){.message{max-width:88%}.report-toggle span{display:none}.report-form{min-width:min(18rem,82vw)}}
</style>
