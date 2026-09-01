/**
 * API 호출을 담당하는 모듈입니다.
 * 각 함수는 백엔드 API 명세의 요구사항 ID를 주석으로 포함합니다.
 */
const API_BASE = '/api/v1';

const apis = {
    isRefreshing: false,
    refreshSubscribers: [],

    subscribeTokenRefresh(callback) {
        this.refreshSubscribers.push(callback);
    },

    onTokenRefreshed(token) {
        this.refreshSubscribers.forEach((callback) => {
            callback(token);
        });

        this.refreshSubscribers = [];
    },

    async request(url, options = {}, skipAlert = false) {
        const headers = {
            ...(options.headers || {})
        };

        if (state.token) {
            headers.Authorization = `Bearer ${state.token}`;
        }

        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers,
            credentials: 'include'
        });

        if (!response.ok) {
            let errorData;

            try {
                errorData = await response.json();
            } catch {
                errorData = {
                    detail: '서버 응답 처리 중 오류가 발생했습니다.'
                };
            }

            let message =
                errorData.detail ||
                '요청 중 오류가 발생했습니다.';

            if (Array.isArray(message)) {
                message = message
                    .map(
                        (error) =>
                            error.msg ||
                            '입력값이 올바르지 않습니다.'
                    )
                    .join(', ');
            }

            const error = new Error(message);
            error.status = response.status;

            if (!skipAlert) {
                console.error(error);
            }

            throw error;
        }

        if (response.status === 204) {
            return null;
        }

        return await response.json();
    },

    // --- Auth ---

    async signup(userData) {
        return await this.request(
            '/auth/signup',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            },
            true
        );
    },

    async login(email, password) {
        return await this.request(
            '/auth/login',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    email,
                    password
                })
            },
            true
        );
    },

    async refresh() {
        return await fetch(
            `${API_BASE}/auth/token/refresh`,
            {
                method: 'POST',
                credentials: 'include'
            }
        );
    },

    async logout() {
        return await this.request('/auth/logout', {
            method: 'POST'
        });
    },

    async getMe() {
        return await this.request('/users/me');
    },

    async updateMe(userData) {
        return await this.request(
            '/users/me',
            {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            },
            true
        );
    },

    async updatePassword(passwordData) {
        return await this.request(
            '/users/me/password',
            {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(passwordData)
            },
            true
        );
    },

    async deleteMe() {
        return await this.request('/users/me', {
            method: 'DELETE'
        });
    },

    // --- Patients ---

    async createPatient(patientData) {
        const genderMap = {
            male: 'M',
            female: 'F',
            M: 'M',
            F: 'F'
        };

        const data = {
            name: patientData.name,
            age: patientData.age,
            gender: genderMap[patientData.gender],
            phone:
                patientData.phone ??
                patientData.phone_number
        };

        return await this.request('/patients', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
    },

    async getPatients(params = {}) {
        const query = new URLSearchParams(params).toString();

        const response = await this.request(
            `/patients${query ? `?${query}` : ''}`
        );

        return response.items ?? response;
    },

    async getPatient(patientId) {
        const patient = await this.request(
            `/patients/${patientId}`
        );

        return {
            ...patient,
            phone_number:
                patient.phone_number ??
                patient.phone
        };
    },

    async updatePatient(patientId, patientData) {
        const data = {
            name: patientData.name,
            phone:
                patientData.phone ??
                patientData.phone_number
        };

        return await this.request(
            `/patients/${patientId}`,
            {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            }
        );
    },

    async deletePatient(patientId) {
        return await this.request(
            `/patients/${patientId}`,
            {
                method: 'DELETE'
            }
        );
    },

    // --- Medical Records ---

    async createMedicalRecord(patientId, formData) {
        return await this.request(
            `/patients/${patientId}/medical-records`,
            {
                method: 'POST',
                body: formData
            }
        );
    },

    async getPatientMedicalRecords(
        patientId,
        params = {}
    ) {
        const query = new URLSearchParams(params).toString();

        const response = await this.request(
            `/patients/${patientId}/medical-records${
                query ? `?${query}` : ''
            }`
        );

        return response.items ?? response;
    },

    async getMedicalRecord(patientId, recordId) {
        return await this.request(
            `/patients/${patientId}/medical-records/${recordId}`
        );
    },

    // --- AI Prediction ---

    async predictPneumonia(recordId, imageFile = null) {
        const options = {
            method: 'POST'
        };

        if (imageFile) {
            const formData = new FormData();
            formData.append('xray_image', imageFile);
            options.body = formData;
        }

        return await this.request(
            `/medical-records/${recordId}/prediction`,
            options
        );
    },

    async getMedicalRecordPrediction(recordId) {
        return await this.request(
            `/medical-records/${recordId}/prediction`
        );
    },

    // --- Admin ---

    async adminGetUsers(params = {}) {
        const query = new URLSearchParams(params).toString();

        const response = await this.request(
            `/admin/users${query ? `?${query}` : ''}`
        );

        return response.items ?? response;
    },

    async adminUpdateUserRole(roleData) {
        return await this.request(
            '/admin/users/role',
            {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(roleData)
            }
        );
    }
};