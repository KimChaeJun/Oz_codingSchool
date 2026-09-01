/**
 * 페이지 렌더링 및 이벤트 핸들러 모음
 */

const pages = {
    async renderHome() {
        const html = await utils.loadTemplate('home');

        if (
            state.currentPage !== '/' &&
            state.currentPage !== '/home'
        ) {
            return;
        }

        const app = document.getElementById('app');
        app.innerHTML = html;

        const actions = document.getElementById('home-actions');

        if (!state.user) {
            actions.innerHTML = `
                <button onclick="navigate('/login')">
                    로그인하여 시작하기
                </button>
            `;
        } else if (state.user.role === 'pending') {
            actions.innerHTML = `
                <p>관리자의 승인을 기다리는 중입니다.</p>
            `;
        } else {
            actions.innerHTML = `
                <button onclick="navigate('/patients')">
                    환자 목록 보기
                </button>
            `;
        }
    },

    async renderLogin() {
        const html = await utils.loadTemplate('login');

        document.getElementById('app').innerHTML = html;
    },

    async renderSignup() {
        const html = await utils.loadTemplate('signup');

        document.getElementById('app').innerHTML = html;

        const phoneInput = document.getElementById('signup-phone');

        if (phoneInput) {
            phoneInput.addEventListener('input', (event) => {
                utils.handlePhoneInput(event);
            });
        }
    },

    async renderPatients(params = {}) {
        const patients = await apis.getPatients(params);
        const html = await utils.loadTemplate('patients');

        if (state.currentPage !== '/patients') {
            return;
        }

        const app = document.getElementById('app');
        app.innerHTML = html;

        const nameInput = document.getElementById('search-name');
        const genderSelect = document.getElementById('filter-gender');
        const minAgeInput = document.getElementById('filter-min-age');
        const maxAgeInput = document.getElementById('filter-max-age');

        if (nameInput && params.name) {
            nameInput.value = params.name;
        }

        if (genderSelect && params.gender) {
            genderSelect.value = params.gender;
        }

        if (minAgeInput && params.min_age) {
            minAgeInput.value = params.min_age;
        }

        if (maxAgeInput && params.max_age) {
            maxAgeInput.value = params.max_age;
        }

        const listBody = document.getElementById('patients-list');

        if (!patients || patients.length === 0) {
            listBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2rem;">
                        검색 결과가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        listBody.innerHTML = patients
            .map((patient) => {
                const gender =
                    patient.gender === 'M' ||
                    patient.gender === 'male'
                        ? '남성'
                        : '여성';

                return `
                    <tr>
                        <td>${patient.id}</td>
                        <td>${patient.name}</td>
                        <td>${patient.age}</td>
                        <td>${gender}</td>
                        <td>
                            ${utils.formatPhoneNumber(
                                patient.phone_number ?? patient.phone
                            )}
                        </td>
                        <td>
                            <button
                                onclick="navigate('/patients/${patient.id}')"
                            >
                                상세보기
                            </button>
                        </td>
                    </tr>
                `;
            })
            .join('');
    },

    async renderPatientCreate() {
        const html = await utils.loadTemplate('patient-create');

        document.getElementById('app').innerHTML = html;

        const phoneInput = document.getElementById('phone_number');

        if (phoneInput) {
            phoneInput.addEventListener('input', (event) => {
                utils.handlePhoneInput(event);
            });
        }
    },

    async renderPatientDetail(patientId) {
        const patient = await apis.getPatient(patientId);
        const records = await apis.getPatientMedicalRecords(patientId);
        const html = await utils.loadTemplate('patient-detail');

        if (!state.currentPage.startsWith('/patients/')) {
            return;
        }

        const app = document.getElementById('app');
        app.innerHTML = html;

        const gender =
            patient.gender === 'M' ||
            patient.gender === 'male'
                ? '남성'
                : '여성';

        document.getElementById('patient-name').innerText =
            `${patient.name} (${gender})`;

        document.getElementById('patient-info').innerText =
            `나이: ${patient.age}세 | 연락처: ${
                utils.formatPhoneNumber(
                    patient.phone_number ?? patient.phone
                )
            }`;

        document.getElementById('update-name').value = patient.name;

        document.getElementById('update-phone').value =
            utils.formatPhoneNumber(
                patient.phone_number ?? patient.phone
            );

        const updatePhoneInput =
            document.getElementById('update-phone');

        if (updatePhoneInput) {
            updatePhoneInput.addEventListener('input', (event) => {
                utils.handlePhoneInput(event);
            });
        }

        document.getElementById('add-record-btn').onclick = () => {
            navigate(
                `/patients/${patientId}/medical-records/create`
            );
        };

        state.currentPatientId = patientId;

        const listBody = document.getElementById('records-list');

        if (!records || records.length === 0) {
            listBody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center;">
                        진료기록이 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        listBody.innerHTML = records
            .map(
                (record) => `
                    <tr>
                        <td>${record.id}</td>
                        <td>${record.chart_number}</td>
                        <td>${record.symptoms}</td>
                        <td>
                            ${new Date(
                                record.created_at
                            ).toLocaleString()}
                        </td>
                        <td>
                            <button
                                onclick="navigate('/patients/${patientId}/medical-records/${record.id}')"
                            >
                                상세보기
                            </button>
                        </td>
                    </tr>
                `
            )
            .join('');
    },

    async renderRecordCreate(patientId) {
        const html = await utils.loadTemplate('record-create');
        const app = document.getElementById('app');

        app.innerHTML = html;

        const imageInput = document.getElementById('xray_image');
        const previewContainer = document.getElementById(
            'image-preview-container'
        );

        imageInput.onchange = (event) => {
            const file = event.target.files[0];

            if (!file) {
                previewContainer.innerHTML =
                    '<p>이미지 미리보기가 여기에 표시됩니다.</p>';
                return;
            }

            const reader = new FileReader();

            reader.onload = (readerEvent) => {
                previewContainer.innerHTML = `
                    <img
                        src="${readerEvent.target.result}"
                        style="max-width: 100%; border-radius: 8px;"
                    >
                `;
            };

            reader.readAsDataURL(file);
        };

        document.getElementById(
            'record-create-form'
        ).onsubmit = (event) => {
            this.handleRecordCreate(event, patientId);
        };

        document.getElementById('cancel-btn').onclick = () => {
            navigate(`/patients/${patientId}`);
        };
    },

    async renderRecordDetail(patientId, recordId) {
        const record = await apis.getMedicalRecord(
            patientId,
            recordId
        );

        let prediction = null;

        try {
            prediction = await apis.getMedicalRecordPrediction(
                recordId
            );
        } catch (error) {
            if (error.status !== 404) {
                throw error;
            }
        }

        const html = await utils.loadTemplate('record-detail');
        const app = document.getElementById('app');

        app.innerHTML = html;

        document.getElementById('record-id').innerText = record.id;
        document.getElementById('chart-number').innerText =
            record.chart_number;
        document.getElementById('symptoms-text').innerText =
            record.symptoms;
        document.getElementById('created-at').innerText =
            new Date(record.created_at).toLocaleString();

        const xrayImage = record.xray_images?.[0];

        if (xrayImage) {
            document.getElementById('xray-img').src =
                xrayImage.image_url;
        } else if (record.xray_image_url) {
            document.getElementById('xray-img').src =
                record.xray_image_url;
        }

        document.getElementById('predict-btn').onclick = () => {
            this.handlePredict(recordId);
        };

        document.getElementById(
            'back-to-patient-btn'
        ).onclick = () => {
            navigate(`/patients/${patientId}`);
        };

        const analysisList =
            document.getElementById('analysis-list');

        if (!prediction) {
            analysisList.innerHTML =
                '<p>저장된 예측 결과가 없습니다.</p>';
            return;
        }

        analysisList.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>수행 일시</th>
                        <th>폐렴 여부</th>
                        <th>Confidence</th>
                        <th>사용 모델</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="${
                        prediction.is_pneumonia
                            ? 'result-positive'
                            : 'result-negative'
                    }">
                        <td>
                            ${new Date(
                                prediction.predicted_at ??
                                    prediction.created_at
                            ).toLocaleString()}
                        </td>
                        <td>
                            <strong>
                                ${
                                    prediction.is_pneumonia
                                        ? 'Positive'
                                        : 'Negative'
                                }
                            </strong>
                        </td>
                        <td>${prediction.confidence}</td>
                        <td>
                            ${
                                prediction.model_name ??
                                prediction.ai_model ??
                                '-'
                            }
                        </td>
                    </tr>
                </tbody>
            </table>
        `;
    },

    async renderMyPage() {
        const html = await utils.loadTemplate('my-page');
        const app = document.getElementById('app');

        app.innerHTML = html;

        document.getElementById('me-email').innerText =
            state.user.email;
        document.getElementById('me-name-display').innerText =
            state.user.name;
        document.getElementById(
            'me-department-display'
        ).innerText = state.user.department;
        document.getElementById('me-gender-display').innerText =
            state.user.gender === 'M' ? '남성' : '여성';
        document.getElementById('me-phone-display').innerText =
            utils.formatPhoneNumber(
                state.user.phone_number ?? state.user.phone
            );
        document.getElementById('me-role-display').innerText =
            state.user.role;

        document.getElementById(
            'update-me-department'
        ).value = state.user.department;

        document.getElementById('update-me-phone').value =
            utils.formatPhoneNumber(
                state.user.phone_number ?? state.user.phone
            );

        const phoneInput =
            document.getElementById('update-me-phone');

        if (phoneInput) {
            phoneInput.addEventListener('input', (event) => {
                utils.handlePhoneInput(event);
            });
        }

        document.getElementById('update-me-form').onsubmit = (event) => {
            this.handleUpdateMe(event);
        };

        document.getElementById(
            'update-password-form'
        ).onsubmit = (event) => {
            this.handleUpdatePassword(event);
        };

        document.getElementById('delete-me-btn').onclick = () => {
            this.handleDeleteMe();
        };
    },

    async renderAdminUsers(params = {}) {
        const users = await apis.adminGetUsers(params);
        const html = await utils.loadTemplate('admin-users');

        if (state.currentPage !== '/admin/users') {
            return;
        }

        const app = document.getElementById('app');
        app.innerHTML = html;

        const listBody =
            document.getElementById('admin-users-list');

        if (!users || users.length === 0) {
            listBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center;">
                        검색 결과가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        listBody.innerHTML = users
            .map(
                (user) => `
                    <tr>
                        <td>${user.id}</td>
                        <td>${user.name}</td>
                        <td>${user.email}</td>
                        <td>${user.department}</td>
                        <td>
                            ${utils.formatPhoneNumber(
                                user.phone_number
                            )}
                        </td>
                        <td>
                            <select
                                onchange="pages.handleRoleUpdate(
                                    ${user.id},
                                    this.value
                                )"
                            >
                                <option value="pending">
                                    승인대기
                                </option>
                                <option value="staff">
                                    일반회원
                                </option>
                                <option value="admin">
                                    관리자
                                </option>
                            </select>
                        </td>
                        <td>
                            ${
                                user.is_active
                                    ? '활성'
                                    : '비활성'
                            }
                        </td>
                    </tr>
                `
            )
            .join('');
    },

    async handleAdminSearch() {
        const query = document.getElementById(
            'admin-search-query'
        ).value;

        const department = document.getElementById(
            'admin-filter-dept'
        ).value;

        const params = new URLSearchParams();

        if (query) {
            params.set('query', query);
        }

        if (department) {
            params.set('department', department);
        }

        const queryString = params.toString();

        navigate(
            `/admin/users${queryString ? `?${queryString}` : ''}`
        );
    },

    resetAdminSearch() {
        navigate('/admin/users');
    },

    async handleRoleUpdate(userId, newRole) {
        try {
            await apis.adminUpdateUserRole({
                user_id: userId,
                new_role: newRole
            });

            utils.showAlert(
                '권한이 변경되었습니다.',
                'success'
            );

            await this.handleAdminSearch();
        } catch (error) {
            utils.showAlert(
                `권한 변경 실패: ${error.message}`,
                'error'
            );
        }
    },

    async handleLogin(event) {
        event.preventDefault();

        const email = document.getElementById('email').value;
        const password =
            document.getElementById('password').value;

        await login(email, password);
    },

    async handleSignup(event) {
    event.preventDefault();

    const departmentValue =
        document.getElementById('signup-department').value;

    const genderValue =
        document.getElementById('signup-gender').value;

    const departmentMap = {
        developer: 'DEV',
        'medical team': 'MEDICAL',
        researcher: 'RESEARCH',
        DEV: 'DEV',
        MEDICAL: 'MEDICAL',
        RESEARCH: 'RESEARCH'
    };

    const genderMap = {
        male: 'M',
        female: 'F',
        M: 'M',
        F: 'F'
    };

    const userData = {
        email: document.getElementById('signup-email').value,
        name: document.getElementById('signup-name').value,
        department: departmentMap[departmentValue],
        gender: genderMap[genderValue],
        phone_number: document
            .getElementById('signup-phone')
            .value.replace(/[^\d]/g, ''),
        password: document.getElementById('signup-password').value
    };

    try {
        await apis.signup(userData);

        utils.showAlert(
            '회원가입이 완료되었습니다. 로그인해주세요.',
            'success'
        );

        navigate('/login');
    } catch (error) {
        utils.showAlert(
            `가입 실패: ${error.message}`,
            'error'
        );
    }
},

    async handlePatientCreate(event) {
    event.preventDefault();

    const patientData = {
        name: document.getElementById('name').value,
        age: parseInt(
            document.getElementById('age').value,
            10
        ),
        gender: document.getElementById('gender').value,
        phone_number: document
            .getElementById('phone_number')
            .value.replace(/[^\d]/g, '')
    };

    try {
        await apis.createPatient(patientData);

        utils.showAlert(
            '환자가 등록되었습니다.',
            'success'
        );

        navigate('/patients');
    } catch (error) {
        utils.showAlert(
            `환자 등록 실패: ${error.message}`,
            'error'
        );
    }
},

    handleSearch() {
        const name = document.getElementById('search-name').value;
        const gender =
            document.getElementById('filter-gender').value;
        const minAge =
            document.getElementById('filter-min-age').value;
        const maxAge =
            document.getElementById('filter-max-age').value;

        const params = new URLSearchParams();

        if (name) {
            params.set('name', name);
        }

        if (gender) {
            params.set('gender', gender);
        }

        if (minAge) {
            params.set('min_age', minAge);
        }

        if (maxAge) {
            params.set('max_age', maxAge);
        }

        const queryString = params.toString();

        navigate(
            `/patients${queryString ? `?${queryString}` : ''}`
        );
    },

    resetSearch() {
        navigate('/patients');
    },

    async handleRecordCreate(event, patientId) {
        event.preventDefault();

        const formData = new FormData();

        formData.append(
            'chart_number',
            document.getElementById('chart_number').value
        );

        formData.append(
            'symptoms',
            document.getElementById('symptoms').value
        );

        const imageFile =
            document.getElementById('xray_image').files[0];

        if (imageFile) {
            formData.append('xray_image', imageFile);
        }

        try {
            await apis.createMedicalRecord(
                patientId,
                formData
            );

            utils.showAlert(
                '진료 기록이 등록되었습니다.',
                'success'
            );

            navigate(`/patients/${patientId}`);
        } catch (error) {
            utils.showAlert(
                `진료 기록 등록 실패: ${error.message}`,
                'error'
            );
        }
    },

    openUpdateModal() {
        document
            .getElementById('update-modal')
            .classList.add('show');
    },

    closeUpdateModal() {
        document
            .getElementById('update-modal')
            .classList.remove('show');
    },

    async handlePatientUpdate(event) {
        event.preventDefault();

        const patientId = state.currentPatientId;

        const updateData = {
            name: document.getElementById('update-name').value,
            phone_number: document
                .getElementById('update-phone')
                .value.replace(/[^\d]/g, '')
        };

        try {
            await apis.updatePatient(
                patientId,
                updateData
            );

            utils.showAlert(
                '환자 정보가 수정되었습니다.',
                'success'
            );

            this.closeUpdateModal();
            await this.renderPatientDetail(patientId);
        } catch (error) {
            utils.showAlert(
                `환자 정보 수정 실패: ${error.message}`,
                'error'
            );
        }
    },

    confirmDeletePatient() {
        document
            .getElementById('delete-modal')
            .classList.add('show');
    },

    closeDeleteModal() {
        document
            .getElementById('delete-modal')
            .classList.remove('show');
    },

    async handlePatientDelete() {
        const patientId = state.currentPatientId;

        try {
            await apis.deletePatient(patientId);

            utils.showAlert(
                '환자 정보와 관련 데이터가 삭제되었습니다.',
                'success'
            );

            this.closeDeleteModal();
            navigate('/patients');
        } catch (error) {
            utils.showAlert(
                `환자 삭제 실패: ${error.message}`,
                'error'
            );
        }
    },

    async handlePredict(recordId) {
        try {
            await apis.predictPneumonia(recordId);

            utils.showAlert(
                'AI 예측이 완료되었습니다.',
                'success'
            );

            navigate(window.location.pathname, false);
        } catch (error) {
            utils.showAlert(
                `AI 예측 실패: ${error.message}`,
                'error'
            );
        }
    }
};