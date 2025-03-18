import $api from ".";

export default class CSRFService {
    static async getCSRF() {
        return $api.get('/csrf/get');
    }
}