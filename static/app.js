const state = {
    user: null,
    token: localStorage.getItem('token'),
    currentPage: '/'
};

async function login(email, password) {
    const errorElement = document.getElementById('login-error');

    if (errorElement) {
        errorElement.style.display = 'none';
    }

    try {
        const data = await apis.login(email, password);

        if (data) {
            state.token = data.access_token;

            localStorage.setItem('token', state.token);
            localStorage.setItem('isLoggedIn', 'true');

            await checkAuth();

            if (state.user?.role === 'pending') {
                await navigate('/');
            } else {
                await navigate('/patients');
            }
        }
    } catch (error) {
        if (errorElement) {
            errorElement.innerText =
                error.message || '로그인 중 오류가 발생했습니다.';
            errorElement.style.display = 'block';
        }
    }
}

async function logout(event) {
    if (event) {
        event.preventDefault();
    }

    try {
        await apis.logout();
    } catch (error) {
        console.error('Logout failed:', error);
    } finally {
        state.token = null;
        state.user = null;

        localStorage.removeItem('token');
        localStorage.removeItem('isLoggedIn');

        updateNav();
        await navigate('/login');
    }
}

async function checkAuth() {
    if (!state.token) {
        return;
    }

    try {
        state.user = await apis.getMe();
        updateNav();
    } catch (error) {
        state.token = null;
        state.user = null;

        localStorage.removeItem('token');
        localStorage.removeItem('isLoggedIn');

        updateNav();
    }
}

function updateNav() {
    const authLink = document.getElementById('auth-link');
    const adminLinkContainer = document.getElementById(
        'admin-link-container'
    );

    if (!authLink || !adminLinkContainer) {
        return;
    }

    if (state.user) {
        document.body.classList.add('logged-in');

        if (state.user.role === 'admin') {
            adminLinkContainer.innerHTML = `
                <li>
                    <a
                        href="/admin/users"
                        onclick="route(event)"
                        class="nav-btn"
                    >
                        회원 관리
                    </a>
                </li>
            `;
        } else {
            adminLinkContainer.innerHTML = '';
        }

        authLink.innerHTML = `
            <span
                class="user-info"
                onclick="navigate('/my-page')"
                style="cursor: pointer;"
            >
                ${state.user.name}(${state.user.department})
            </span>
            <a
                href="#"
                onclick="logout(event)"
                class="nav-btn logout-btn"
            >
                로그아웃
            </a>
        `;
    } else {
        document.body.classList.remove('logged-in');
        adminLinkContainer.innerHTML = '';

        authLink.innerHTML = `
            <a
                href="/login"
                onclick="route(event)"
                class="nav-btn login-btn"
            >
                로그인
            </a>
        `;
    }
}

function route(event) {
    event.preventDefault();

    const path =
        event.currentTarget.getAttribute('href') ||
        event.target.getAttribute('href');

    navigate(path);
}

async function navigate(path, pushState = true) {
    if (pushState) {
        window.history.pushState({}, '', path);
    }

    const url = new URL(window.location.origin + path);
    const pathname = url.pathname;
    const searchParams = Object.fromEntries(url.searchParams);

    state.currentPage = pathname;

    const app = document.getElementById('app');
    app.innerHTML = '<div class="card">로딩 중...</div>';

    try {
        const publicPaths = ['/', '/home', '/login', '/signup'];

        if (!state.user && !publicPaths.includes(pathname)) {
            await navigate('/login');
            return;
        }

        if (
            state.user &&
            state.user.role === 'pending' &&
            !publicPaths.includes(pathname)
        ) {
            utils.showAlert(
                '승인 대기 중인 사용자입니다.',
                'error',
                '접근 제한'
            );

            await navigate('/');
            return;
        }

        if (
            pathname === '/admin/users' &&
            state.user?.role !== 'admin'
        ) {
            utils.showAlert(
                '관리자 권한이 필요합니다.',
                'error',
                '접근 제한'
            );

            await navigate('/');
            return;
        }

        if (pathname === '/' || pathname === '/home') {
            await pages.renderHome();
        } else if (pathname === '/login') {
            await pages.renderLogin();
        } else if (pathname === '/signup') {
            await pages.renderSignup();
        } else if (pathname === '/patients') {
            await pages.renderPatients(searchParams);
        } else if (pathname === '/patients/create') {
            await pages.renderPatientCreate();
        } else if (
            pathname.startsWith('/patients/') &&
            pathname.endsWith('/medical-records/create')
        ) {
            const patientId = pathname.split('/')[2];

            await pages.renderRecordCreate(patientId);
        } else if (
            pathname.startsWith('/patients/') &&
            pathname.includes('/medical-records/') &&
            !pathname.endsWith('/create')
        ) {
            const pathParts = pathname.split('/');
            const patientId = pathParts[2];
            const recordId = pathParts[4];

            await pages.renderRecordDetail(patientId, recordId);
        } else if (pathname === '/my-page') {
            await pages.renderMyPage();
        } else if (pathname === '/admin/users') {
            await pages.renderAdminUsers(searchParams);
        } else if (pathname.startsWith('/patients/')) {
            const patientId = pathname.split('/')[2];

            await pages.renderPatientDetail(patientId);
        } else {
            app.innerHTML = `
                <div class="card">
                    <h2>404</h2>
                    <p>페이지를 찾을 수 없습니다.</p>
                </div>
            `;
        }
    } catch (error) {
        app.innerHTML = `
            <div class="card">
                <h2>오류</h2>
                <p>${error.message}</p>
                <button onclick="navigate('/')">
                    홈으로
                </button>
            </div>
        `;
    }
}

window.onpopstate = () => {
    navigate(
        window.location.pathname + window.location.search,
        false
    );
};

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();

    await navigate(
        window.location.pathname + window.location.search,
        false
    );
});