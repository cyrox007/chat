<template>
	<div class="delete-profile-confirm" :class="props.modalShow ? 'active' : ''">
		<div class="delete-profile-form">
			<h2>Удалить ваш профиль?</h2>
			<div class="btns">
				<button @click="$emit('confirm')">ДА</button>
				<button @click="$emit('close')">НЕТ</button>
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	modalShow: {
		type: Boolean,
		required: true,
		default: false
	},
});
</script>

<style>
.delete-profile-confirm {
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
.delete-profile-confirm.active {
	position: fixed;
	height: auto;
	width: auto;
	opacity: 1;
}
</style>

