import $api from ".";

export default class UsersServices {
    static async get_users_by_uids(uids) {
        return $api.post(`/users/by-uids`, {user_uids: uids});
    }
}