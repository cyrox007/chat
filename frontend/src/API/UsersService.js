import $api from ".";

export default class UsersServices {
    static async get_users_by_uids(uids) {
        const response = await $api.post('/identity/v2/personas/batch', { account_uids: uids });
        const users = response.data.personas.map((persona) => ({
            uid: persona.uid,
            persona_uid: persona.persona_uid,
            username: persona.handle,
            display_name: persona.display_name,
            avatar: persona.avatar,
            social_intent: persona.social_intent,
        }));
        return {
            ...response,
            data: { status: 'ok', users },
        };
    }

    static async get_user_by_uid(uid) {
        const response = await $api.get(`/identity/v2/profiles/${uid}`);
        const profile = response.data.profile;
        return {
            ...response,
            data: {
                status: 'ok',
                user: {
                    uid: profile.uid,
                    persona_uid: profile.persona_uid,
                    username: profile.handle,
                    display_name: profile.display_name,
                    avatar: profile.avatar,
                    bio: profile.bio,
                    city: profile.city,
                    country: profile.country,
                    social_intent: profile.social_intent,
                    global_role: profile.role || 'user',
                },
            },
        };
    }

    static async getUserStatuses(user_uids) {
        return $api.post('/users/statuses', { user_ids: user_uids });
    }

    static async deleteProfile() {
        return $api.delete('/users/delete');
    }

    static async updateProfile(uid, data) {
        return $api.put('/users/update', { user_uid: uid, data });
    }
}
