# TODO / 후속 작업

Day별 문서에 흩어놓지 않고, Day(발생 시점), 항목, 중요도, 긴급도, 해결시점, 상태를 표로 제시함.
새로운 후속 작업이 생기면 해당 Day 문서에 근거만 남기고, 실제 TODO는 여기에 추가.

## Docker 단계

| Day | 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|---|
| Day8 | [Alembic 멀티헤드 정리](#alembic-멀티헤드-정리) | 높음 | 높음 | day10 시작 전 | 🟡 PR #27 리뷰 대기 |
| Day6 | `(record_id, ai_model)` UniqueConstraint 추가 | - | - | Alembic 정리 후 | ⬜ 미착수 |
| Day6 | `IntegrityError` 처리 | - | - | UniqueConstraint 후 | ⬜ 미착수 |
| Day10 | [Docker 이미지 용량 개선](#docker-이미지-용량-개선) | 보통 | 낮음 | 10일차 의존성 분리 | ✅ 완료 (2026-09-04) |
| Day10 | [docker-compose.yml volumes 전략 재검토](#docker-composeyml-volumes-전략-재검토) | 보통 | 낮음 | 10일차 AI worker 전 | 🟡 dev 확정 · prod는 12일차 예정 |
| - | `DB_USER=root` 사용 방식 재검토 | 높음 | 중간 | 12일차 배포 설정 전 | ⬜ 미착수 |

#### Alembic 멀티헤드 정리
- 2026-09-02 Docker 테스트 2(회원가입/로그인)에서 실제로 이 문제 때문에 막힘: 새 `mysql_volume`에 스키마가 없어 `alembic upgrade head`를 돌리려 했으나 head가 2개(`20260827_02`, `2a635f4b60e5`)라 명령 자체가 실패함. `alembic upgrade 20260827_02`로 리비전을 직접 지정해 우회 실행 후 테스트 통과.
- `2a635f4b60e5_add_initial_schema.py`는 본인이 3일차에 작성한 초기 스키마이며, 팀에서 채택된 `20260826_01`(chaeyun) → `20260827_02`(팀장님) 계보와 동일한 5개 테이블을 중복 생성함. 어느 브랜치도 이 파일을 부모로 삼는 후속 migration이 없음. 현재 Docker 테스트 DB에는 해당 migration이 적용되지 않았음을 확인함.
- 2026-09-03 채연님 로컬에서 `uv run alembic heads` 확인 결과 `20260827_02 (head)` 한 줄만 출력됨 → 채연님 로컬은 영향 없음 확인 완료.
- 해결: 별도 PR [#27](https://github.com/KimChaeJun/Oz_codingSchool/pull/27)(`fix/remove-duplicate-migration` → `main`)로 이미 분리 처리함. 2026-09-02 생성, 팀장님(day10까지 부재) 리뷰 대기 중, 아직 merge 안 됨. day8 브랜치 자체는 이 파일을 그대로 갖고 있음(별도 PR이라 안 건드림). PR merge 확인되면 위 표 상태를 완료로 변경.
- **day10 시작 전 필수 조치**: day9/day10을 지금의 day8(또는 day9) 브랜치에서 그냥 이어서 새로 파기만 하면, 이 파일이 그대로 따라와서 day10에서 `alembic upgrade head`가 다시 실패함(단순 브랜치 생성은 merge가 아니라 파일이 안 지워짐, `git merge-tree`로 시뮬레이션해 확인). 반드시 day10 시작 전에 (a) PR #27이 merge된 최신 `main`을 작업 브랜치에 merge하거나, (b) 작업 브랜치에서 이 파일을 직접 삭제한 뒤 진행할 것.
- **2026-09-04 처리**: (b) 방식으로 day10 브랜치(`hyeseong_day10`)에서 직접 파일 삭제, `alembic heads`가 `20260827_02` 하나만 남는 것 확인 후 커밋(`436cc17`). day9 이하 브랜치와 main은 건드리지 않음. **main 자체의 최종 해결은 PR #27(또는 동일 삭제를 포함한 day10 PR)이 merge된 뒤로 남아있음** — merge 후 `main`에서 `alembic heads` 재확인 필요.

#### Docker 이미지 용량 개선
- app과 ai(worker) 의존성을 `pyproject.toml`의 `[project.optional-dependencies]`로 분리(`app`/`ai` extra), 공통 `dependencies`엔 `redis`만 유지.
- `app/Dockerfile`은 `--extra app`, `worker/Dockerfile`은 `--extra ai`로 설치.
- 검증: app 이미지 — `docker compose build fastapi` 로그에 torch/torchvision/pillow 없음 확인 + `docker compose run --rm --entrypoint "" fastapi python -c "..."`로 `importlib.util.find_spec('torch') is None` 등 직접 확인.
- 검증: worker 이미지 — `docker build -f worker/Dockerfile` 로그에 `torch==2.13.0`, `torchvision==0.28.0`, `pillow==12.3.0`, `redis==8.1.0` 정상 설치 확인(= AI 의존성은 worker에만 들어감).
- 커밋: `64b277f`(pyproject/uv.lock/app Dockerfile), `050a1b5`(worker/Dockerfile).

#### docker-compose.yml volumes 전략 재검토
- 로컬 개발/Compose 통합 테스트용으로는 fastapi와 동일하게 `ai-worker`에도 `.:/app` 전체 bind mount를 채택해 `media/` 공유 문제를 해결함 (E2E로 동작 확인, 커밋 `050a1b5`).
- **재검토를 다 마친 건 아님** — 이건 dev 환경 한정 결정이고, day12 production compose(`docker-compose.prod.yml`)에서는 다른 구조가 필요할 것으로 예상됨: `static_volume`/`media_volume` named volume으로 fastapi·ai-worker·nginx가 공유, 모델 파일(`worker/models/*.pth`)은 이미지에 안 담고 별도 마운트 + scp로 EC2에 전달. day12 착수 시 별도로 다시 결정할 것.

## Day7 (프론트 연동)

| Day | 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|---|
| Day7 | 프론트에서 `heatmap_url: null` 처리 (현재 Hitmap 미생성이라 항상 null) | - | - | - | ⬜ 미착수 |
| Day7 | POST `200`/`201` 둘 다 성공으로 처리 (캐시 재사용 시 200) | - | - | - | ⬜ 미착수 |
| Day7 | 별도 프론트 서버 사용 시 CORS 설정 필요 여부 확인 | - | - | - | ⬜ 미착수 |

## QA

| Day | 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|---|
| Day6 | [동시 요청 중복 생성 방지 테스트](#동시-요청-중복-생성-방지-테스트) | - | - | UniqueConstraint 적용 후 | ⬜ 미착수 (xfail로 문서화, 2026-09-04) |
| Day6 | [API 전체 응답시간 측정(NFR-PRED-002, 3초 이내)](#api-전체-응답시간-측정) | - | - | - | ✅ 완료 (2026-09-04) |
| Day8 | [Compose DB 통신 검증](#compose-db-통신-검증) | 높음 | 중간 | - | ✅ 완료 (2026-09-02) |
| - | `app/apis/user.py` 미사용 코드 정리 검토 | 낮음 | 낮음 | 11일차 최종 정리 전 | ⬜ 미착수 |

#### Compose DB 통신 검증
- 회원가입·로그인·`GET /users/me`로 실제 DB 쿼리 성공 확인함. `/healthcheck`·`/docs`는 DB 연결 없이도 성공하므로 이것만으로는 검증되지 않아, 별도로 DB를 쓰는 API까지 호출해서 확인함.
- **주의**: 검증 전 `docker compose exec fastapi uv run alembic upgrade 20260827_02`를 수동으로 실행해야 했음 — 새 `mysql_volume`엔 테이블이 없었고(`Table 'ai_health.users' doesn't exist`), `docker-compose.yml`엔 자동 마이그레이션이 없음. 이 수동 실행 없이는 DB를 쓰는 모든 API가 500 에러남. **2026-09-04 기준 여전히 자동화 안 됨** — day12 production compose(`entrypoint: sh -c "uv run alembic upgrade head && ..."`)에서 해결 예정.

#### 동시 요청 중복 생성 방지 테스트
- 2026-09-04, day10 Redis Queue/Worker 분리 작업 중 `tests/test_prediction_apis.py::test_concurrent_predict_requests_may_create_duplicate_rows`에 `@pytest.mark.xfail(strict=False)` 표시함. 여전히 미해결이지만, CI에서 이 실패가 "알려진 한계"임을 명확히 구분되게 함(진짜 회귀와 섞이지 않도록).
- 근본 해결(UniqueConstraint + IntegrityError 처리)은 하지 않음 — day10 범위 밖.

#### API 전체 응답시간 측정
- 측정 환경: 2026-09-04, 실제 Docker 전체 스택(fastapi+ai-worker+redis+mysql), `curl -w`로 각 시나리오 **1회씩** 측정(반복 측정 아님 — 여러 번 측정한 평균은 아니라는 점 주의).
  - 최초 추론(Redis Queue+Worker 왕복 포함): 0.87초
  - 동일 record 재요청(DB 캐시): 0.007초
  - 새 record, 워커 워밍업 상태: 0.08초
- 목표(3초 이내) 충분히 충족. `worker/model.py`의 `test_model_inference_performance_and_caching`(모델 단독 추론 시간, pytest 회귀 테스트로 매번 자동 측정됨)과는 별개로, 이건 Redis 왕복을 포함한 전체 파이프라인 기준 1회성 수동 측정임.

## 향후 개선

| Day | 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|---|
| - | 목록 API(users, patients, medical-records, predictions)에 pagination 추가 — 각 Day URD에 개별 명시 안 됐지만, 데이터 누적 시 필요 | - | - | - | ⬜ 미착수 |

## 배포 전 보류 항목

| Day | 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|---|
| Day7 | [`Cache-Control: no-store` 추가](#cache-control-no-store-추가) | 높음 | 중간 | day12 배포 전 별도 bugfix | ⬜ 미착수 |
| Day7 | 테스트 잔여 계정 정리 검토 | - | - | 팀 확인 후, day12 공개 배포 전 | ⬜ 미착수 |
| Day7 | Pydantic 영어 검증 메시지 노출 | 보통 | - | - | ⬜ 미착수 |
| Day7 | 404 오류 범용 화면 표시 | 보통 | - | - | ⬜ 미착수 |

#### `Cache-Control: no-store` 추가
- 대상: `app/apis/user_apis.py`의 `GET /me` (`app/apis/user.py`는 어디서도 import되지 않는 미사용 코드라 대상 아님)
- 원인 추정: 응답에 캐시 방지 헤더가 없어 브라우저가 URL 기준으로 응답 본문을 캐시함.
- 현재 상태: Day7 실브라우저 테스트 중 같은 브라우저에서 로그아웃 후 다른 계정으로 로그인해도 `/users/me`가 이전 계정 정보를 그대로 반환하는 현상을 2회 재현 확인(2026-09-01). Day7 범위에서는 수정하지 않음.
- 긴급도 재평가(2026-09-03): 현재 프로젝트는 실서비스가 아니고 팀원 간 기기 공유도 없어 긴급도는 중간으로 재평가함. 단, 동일 브라우저에서 계정을 바꾸는 경우 이전 응답이 표시될 수 있으므로 별도 bugfix 대상으로 유지함. 캐시 방지 헤더 자체는 일반적으로 지켜야 할 관행이라 중요도는 유지.
- 해결 방향: 인증된 사용자 정보를 다루는 API 응답(`/users/me` 등)에 `Cache-Control: no-store` 등 캐시 방지 설정 검토. 별도 bugfix commit으로 처리.
- **2026-09-04 재확인**: day10 진행 중 재검토함. AWS로 실제 공개 배포되는 day12 전에는 해결하는 게 안전하다고 판단해 해결 시점을 "day12 배포 전"으로 재확정. day10 범위는 아니라 이번엔 수정하지 않음.

#### 테스트 잔여 계정 정리 검토
- 대상(코드/문서/시드 어디에서도 참조되지 않고, 계정명 자체가 단발성 테스트 목적임이 명확한 것만): `signup-test@example.com`(id 5, "회가입테스트"), `final-test@example.com`(id 6, "최종테스트"), `password-test@example.com`(id 7, "비번테스트"), `live-http-check@example.com`(id 24, "라이브HTTP확인").
- `admin123@test.com`(id 12), `testadmin@example.com`(id 14), `user1@example.com`(id 15)는 삭제 대상에서 제외: 실사용 여부를 판단할 근거가 부족함(2026-09-01 조사 결과, 상세는 Day7 대화 기록 참고).
- **2026-09-04 재확인**: 실제 AWS에 공개 배포하기 전에는 정리 권장(테스트 계정에 실제 비밀번호·개인정보가 결합돼 있다면 배포 전 반드시 제거/비활성화 필요). 다만 삭제는 실제 데이터를 지우는 작업이라 여전히 팀 확인 후 진행. day10 범위 아니라 이번엔 삭제하지 않음.
- Day7에서는 삭제하지 않음. 팀 확인 후 대상 확정되면 정리.

#### Pydantic 영어 검증 메시지 노출
- 환자 등록/수정 등 잘못된 입력으로 422가 발생할 때 백엔드의 Pydantic 검증 메시지가 영어 원문 그대로 사용자에게 표시됨. 기능 자체는 정상적으로 422를 반환하고 크래시도 없으므로 UX 개선사항으로 기록. Day7에서 새로 발생한 버그가 아니라 기존 프론트 오류 메시지 처리의 개선사항임.
- 해결 방향: 향후 `apis.js`의 오류 메시지 매핑을 보완하여 사용자 친화적인 한국어 메시지를 표시.

#### 404 오류 범용 화면 표시
- 존재하지 않는 환자/진료기록 ID를 요청하면 백엔드는 정상적으로 404를 반환함. 프론트에서는 현재 범용 오류 카드(예: "찾을 수 없습니다")로 처리되어 구체적인 HTTP 상태나 오류 유형은 표시하지 않음. 크래시나 기능 오류는 아니므로 UX 개선사항으로 기록. 이것 역시 Day7에서 새로 만든 오류 처리 로직이 아니라 기존 프론트 구조의 개선사항임.
- 해결 방향: 향후 필요에 따라 404 등 HTTP 상태별 사용자 메시지를 구분하는 방향으로 개선.

## 근거 문서
- `docs/6일차_폐렴예측_API_설계.md` 4.4장, 11장
