import $api from ".";

export default class UsersServices {
    static async get_users_by_uids(uids) {
        return $api.post(`/users/by-uids`, {user_uids: uids});
    }
    static async get_user_by_uid(uid) {
        return $api.get(`/users/${uid}`);
    }
    static async getUserStatuses(user_uids) {    
        return await $api.post('/users/statuses', {user_ids: user_uids})
    }
    static async deleteProfile(user_uids) {    
        return await $api.delete('/users/delete', {user_ids: user_uids})
    }
    static async updateProfile(uid, data) {    
        return await $api.put('/users/update', {user_uid: uid, data: data})
    }
}