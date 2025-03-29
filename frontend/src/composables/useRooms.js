// src/composables/useRooms.js
import { ref } from 'vue';
import RoomsService from '@/API/RoomsService';

export function useRooms() {
    const rooms = ref([]);
    const isLoading = ref(false);

    const loadRooms = async () => {
        isLoading.value = true;
        try {
            const data = await RoomsService.get_rooms();
            rooms.value = data.rooms || [];
        } catch (error) {
            console.error('Ошибка загрузки комнат:', error);
        } finally {
            isLoading.value = false;
        }
    };

    return { rooms, isLoading, loadRooms };
}