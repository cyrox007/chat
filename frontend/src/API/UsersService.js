import $api from ".";

export default class UsersServices {
    static async get_users_by_uids(uids) {
        return $api.post(`/users/by-uids`, {user_uids: uids});
    }
    static async get_user_by_uid(uid) {
        return $api.get(`/users/${uid}`);
    }
}