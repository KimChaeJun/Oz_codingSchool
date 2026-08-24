# GitHub 초보자를 위한 브랜치 설정 및 사용법

GitHub 협업에서는 `main` 브랜치에서 바로 작업하지 않고, **자신의 작업용 브랜치를 생성해서 작업한 뒤 Pull Request(PR)를 통해 병합하는 방식​**을 권장합니다.

처음 GitHub를 사용하는 사람도 따라 할 수 있도록 필요한 과정만 순서대로 정리했습니다.

---

## 1. Git 설치 확인

터미널 또는 Git Bash에서 아래 명령어를 입력합니다.

```bash
git --version
```

다음과 같이 버전이 출력되면 Git이 정상적으로 설치되어 있습니다.

```text
git version 2.x.x
```

설치되어 있지 않다면 Git을 먼저 설치해야 합니다.

---

# 2. GitHub Repository 가져오기

팀에서 사용하는 GitHub Repository 주소를 복사합니다.

예시:

```text
https://github.com/사용자명/project.git
```

터미널에서 프로젝트를 저장할 위치로 이동한 후 아래 명령어를 실행합니다.

```bash
git clone https://github.com/사용자명/project.git
```

다운로드된 프로젝트 폴더로 이동합니다.

```bash
cd project
```

---

# 3. 현재 브랜치 확인

```bash
git branch
```

예시:

```text
* main
```

`*`가 붙어 있는 브랜치가 현재 사용 중인 브랜치입니다.

---

# 4. main 브랜치 최신 상태로 업데이트

새로운 브랜치를 만들기 전에 `main` 브랜치를 최신 상태로 맞춰주는 것이 좋습니다.

```bash
git switch main
```

그다음 GitHub의 최신 내용을 가져옵니다.

```bash
git pull origin main
```

---

# 5. 작업용 브랜치 생성

`main`에서 직접 작업하지 않고 자신의 작업용 브랜치를 생성합니다.

```bash
git switch -c 브랜치명
```

예시:

```bash
git switch -c feature/login
```

이 명령어는

1. `feature/login` 브랜치를 생성하고
2. 생성한 브랜치로 이동

하는 두 작업을 동시에 수행합니다.

확인:

```bash
git branch
```

결과:

```text
* feature/login
  main
```

---

# 6. 브랜치 이름 작성 방법

브랜치 이름은 **어떤 작업을 하는 브랜치인지 알아볼 수 있게 작성**합니다.

추천 형식:

```text
feature/기능명
fix/버그명
docs/문서명
refactor/작업명
```

예시:

```text
feature/login
feature/signup
feature/main-page

fix/login-error
fix/header-layout

docs/readme

refactor/user-api
```

간단한 팀 프로젝트라면 자신의 이름을 사용할 수도 있습니다.

```text
feature/chaejun
feature/minsu
```

또는

```text
chaejun/login
minsu/main
```

처럼 사용할 수도 있습니다.

---

# 7. 파일 작업하기

브랜치를 만든 이후 평소처럼 VSCode 등에서 코드를 수정합니다.

작업이 끝났다면 변경된 파일을 확인합니다.

```bash
git status
```

예시:

```text
modified: src/App.jsx
modified: src/Login.jsx
```

---

# 8. 변경 내용 Git에 추가

전체 변경 파일을 추가하려면:

```bash
git add .
```

특정 파일만 추가하려면:

```bash
git add 파일명
```

예시:

```bash
git add src/Login.jsx
```

---

# 9. Commit 생성

변경 내용을 하나의 작업 단위로 저장합니다.

```bash
git commit -m "커밋 메시지"
```

예시:

```bash
git commit -m "feat: 로그인 페이지 구현"
```

추천 커밋 형식:

```text
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: CSS 및 디자인 수정
refactor: 코드 구조 개선
```

예시:

```bash
git commit -m "feat: 회원가입 기능 추가"
```

```bash
git commit -m "fix: 로그인 오류 수정"
```

```bash
git commit -m "style: 메인 페이지 디자인 수정"
```

---

# 10. 자신의 브랜치를 GitHub에 업로드

처음 만든 브랜치는 GitHub에 존재하지 않기 때문에 아래 명령어를 실행합니다.

```bash
git push -u origin 브랜치명
```

예시:

```bash
git push -u origin feature/login
```

`-u` 옵션을 처음 한 번 사용하면 이후부터는 간단하게

```bash
git push
```

만 입력해도 됩니다.

---

# 11. GitHub에서 Pull Request 생성

브랜치를 GitHub에 `push`하면 GitHub Repository 페이지에서 다음과 같은 버튼이 나타납니다.

```text
Compare & pull request
```

해당 버튼을 클릭합니다.

PR 설정에서 다음 내용을 확인합니다.

```text
base: main
compare: feature/login
```

즉,

```text
feature/login → main
```

방향으로 병합을 요청하는 것입니다.

PR 제목을 작성합니다.

예시:

```text
로그인 페이지 구현
```

설명에는 작업한 내용을 간단히 작성합니다.

```text
- 로그인 UI 구현
- 아이디/비밀번호 입력 기능 구현
- 로그인 API 연동
```

마지막으로

```text
Create pull request
```

버튼을 누릅니다.

---

# 12. PR Merge

팀원이 코드를 확인한 뒤 문제가 없다면 PR을 `main` 브랜치에 병합합니다.

GitHub에서

```text
Merge pull request
```

를 선택합니다.

병합이 완료되면 자신의 작업 내용이 `main` 브랜치에 반영됩니다.

---

# 13. 다음 작업 시작하기

기존 작업이 `main`에 병합되었다면 다음 작업 전에 다시 `main`으로 이동합니다.

```bash
git switch main
```

최신 내용을 가져옵니다.

```bash
git pull origin main
```

그리고 새로운 작업용 브랜치를 생성합니다.

```bash
git switch -c feature/새로운기능
```

예시:

```bash
git switch -c feature/mypage
```

---

# 전체 작업 흐름

GitHub 협업 시 기본적인 흐름은 다음과 같습니다.

```text
1. main 브랜치 이동
        ↓
2. 최신 코드 pull
        ↓
3. 작업 브랜치 생성
        ↓
4. 코드 수정
        ↓
5. git add
        ↓
6. git commit
        ↓
7. git push
        ↓
8. Pull Request 생성
        ↓
9. 코드 확인
        ↓
10. main에 Merge
```

실제 명령어만 보면 다음과 같습니다.

```bash
# 1. main 이동
git switch main

# 2. 최신 코드 가져오기
git pull origin main

# 3. 작업 브랜치 생성
git switch -c feature/login

# 4. 코드 작업 후 변경사항 확인
git status

# 5. 변경 파일 추가
git add .

# 6. Commit
git commit -m "feat: 로그인 기능 구현"

# 7. GitHub에 브랜치 업로드
git push -u origin feature/login
```

이후 GitHub에서 Pull Request를 생성합니다.

---

# 이미 만든 브랜치로 이동하기

브랜치 목록 확인:

```bash
git branch
```

원하는 브랜치로 이동:

```bash
git switch 브랜치명
```

예시:

```bash
git switch feature/login
```

---

# GitHub에 있는 다른 사람의 브랜치 가져오기

먼저 GitHub의 최신 브랜치 정보를 가져옵니다.

```bash
git fetch
```

원격 브랜치를 확인합니다.

```bash
git branch -a
```

예시:

```text
main
remotes/origin/feature/login
remotes/origin/feature/signup
```

원격 브랜치를 자신의 컴퓨터로 가져오려면:

```bash
git switch --track origin/브랜치명
```

예시:

```bash
git switch --track origin/feature/login
```

---

# 주의사항

## 1. main에서 직접 작업하지 않기

가능하면 아래 상태에서 코드를 수정하지 않습니다.

```text
* main
```

작업 전 반드시 자신의 브랜치를 생성합니다.

```bash
git switch -c feature/작업명
```

---

## 2. 작업 시작 전에 pull 하기

다른 팀원이 코드를 수정했을 수 있기 때문에 작업 시작 전에는

```bash
git switch main
git pull origin main
```

을 실행합니다.

---

## 3. 다른 사람 브랜치에 임의로 push 하지 않기

각자 자신의 브랜치에서 작업합니다.

예:

```text
feature/login       ← 로그인 담당
feature/signup      ← 회원가입 담당
feature/mypage      ← 마이페이지 담당
```

---

## 4. 너무 많은 작업을 한 번에 commit하지 않기

좋은 예:

```text
feat: 로그인 UI 구현
feat: 로그인 API 연동
fix: 로그인 실패 메시지 수정
```

좋지 않은 예:

```text
수정
작업
최종
진짜최종
진짜최종2
```

---

# 초보자용 핵심 명령어 정리

| 명령어 | 의미 |
|---|---|
| `git clone URL` | GitHub 프로젝트 다운로드 |
| `git branch` | 브랜치 목록 확인 |
| `git switch 브랜치명` | 브랜치 이동 |
| `git switch -c 브랜치명` | 새로운 브랜치 생성 + 이동 |
| `git status` | 변경된 파일 확인 |
| `git add .` | 변경 파일 추가 |
| `git commit -m "메시지"` | 변경 내용 저장 |
| `git pull` | GitHub의 최신 코드 가져오기 |
| `git push` | 내 코드를 GitHub에 업로드 |
| `git fetch` | GitHub의 최신 브랜치 정보 가져오기 |

---

# 이것만 기억하면 됩니다

```bash
git switch main
git pull origin main

git switch -c feature/내작업

# 코드 작업

git add .
git commit -m "feat: 작업 내용"
git push -u origin feature/내작업
```

그리고 GitHub에서

```text
Pull Request 생성
        ↓
코드 확인
        ↓
main에 Merge
```

하면 됩니다.

> **핵심 원칙:**  
> `main`은 완성된 코드를 보관하는 브랜치로 사용하고, 각자 별도의 브랜치를 만들어 작업한 뒤 PR을 통해 `main`에 합칩니다.