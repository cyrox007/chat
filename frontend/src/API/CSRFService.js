import { ensureCsrfToken } from ".";

export default class CSRFService {
    static async getCSRF() {
        return ensureCsrfToken();
    }
}
