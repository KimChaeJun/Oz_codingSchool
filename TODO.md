# TODO / 후속 작업

Day별 문서에 흩어놓지 않고, "지금 당장 하지 않기로 한 것"을 전부 여기 한 곳에 모은다.
새로운 후속 작업이 생기면 해당 Day 문서에 근거만 남기고, 실제 TODO는 여기에만 추가한다.

## Docker 단계

| 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|
| [Alembic 멀티헤드 정리](#alembic-멀티헤드-정리) | 높음 | 높음 | day10 시작 전 | 🟡 PR #27 리뷰 대기 |
| `(record_id, ai_model)` UniqueConstraint 추가 | - | - | Alembic 정리 후 | ⬜ 미착수 |
| `IntegrityError` 처리 | - | - | UniqueConstraint 후 | ⬜ 미착수 |
| Docker 이미지 용량 개선 | 보통 | 낮음 | 10일차 의존성 분리 | ⬜ 미착수 |
| docker-compose.yml volumes 전략 재검토 | 보통 | 낮음 | 10일차 AI worker 전 | ⬜ 미착수 |
| `DB_USER=root` 사용 방식 재검토 | 높음 | 중간 | 12일차 배포 설정 전 | ⬜ 미착수 |

#### Alembic 멀티헤드 정리
- 2026-09-02 Docker 테스트 2(회원가입/로그인)에서 실제로 이 문제 때문에 막힘: 새 `mysql_volume`에 스키마가 없어 `alembic upgrade head`를 돌리려 했으나 head가 2개(`20260827_02`, `2a635f4b60e5`)라 명령 자체가 실패함. `alembic upgrade 20260827_02`로 리비전을 직접 지정해 우회 실행 후 테스트 통과.
- `2a635f4b60e5_add_initial_schema.py`는 본인이 3일차에 작성한 초기 스키마이며, 팀에서 채택된 `20260826_01`(chaeyun) → `20260827_02`(팀장님) 계보와 동일한 5개 테이블을 중복 생성함. 어느 브랜치도 이 파일을 부모로 삼는 후속 migration이 없음. 현재 Docker 테스트 DB에는 해당 migration이 적용되지 않았음을 확인함. 다른 팀원의 로컬 DB 적용 여부는 확인하지 않음.
- 해결: 별도 PR [#27](https://github.com/KimChaeJun/Oz_codingSchool/pull/27)(`fix/remove-duplicate-migration` → `main`)로 이미 분리 처리함. 2026-09-02 생성, 팀장님(day10까지 부재) 리뷰 대기 중, 아직 merge 안 됨. day8 브랜치 자체는 이 파일을 그대로 갖고 있음(별도 PR이라 안 건드림). PR merge 확인되면 위 표 상태를 완료로 변경.
- **day10 시작 전 필수 조치**: day9/day10을 지금의 day8(또는 day9) 브랜치에서 그냥 이어서 새로 파기만 하면, 이 파일이 그대로 따라와서 day10에서 `alembic upgrade head`가 다시 실패함(단순 브랜치 생성은 merge가 아니라 파일이 안 지워짐, `git merge-tree`로 시뮬레이션해 확인). 반드시 day10 시작 전에 (a) PR #27이 merge된 최신 `main`을 작업 브랜치에 merge하거나, (b) 작업 브랜치에서 이 파일을 직접 삭제한 뒤 진행할 것.

## Day7
- [ ] 프론트에서 `heatmap_url: null` 처리 (현재 Hitmap 미생성이라 항상 null)
- [ ] POST `200`/`201` 둘 다 성공으로 처리 (캐시 재사용 시 200)
- [ ] 별도 프론트 서버 사용 시 CORS 설정 필요 여부 확인

## QA

| 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|
| 동시 요청 중복 생성 방지 테스트 | - | - | UniqueConstraint 적용 후 | ⬜ 미착수 |
| API 전체 응답시간 측정(NFR-PRED-002, 3초 이내) | - | - | - | ⬜ 미착수 |
| [Compose DB 통신 검증](#compose-db-통신-검증) | 높음 | 중간 | - | ✅ 완료 (2026-09-02) |
| `app/apis/user.py` 미사용 코드 정리 검토 | 낮음 | 낮음 | 11일차 최종 정리 전 | ⬜ 미착수 |

#### Compose DB 통신 검증
- 회원가입·로그인·`GET /users/me`로 실제 DB 쿼리 성공 확인함. `/healthcheck`·`/docs`는 DB 연결 없이도 성공하므로 이것만으로는 검증되지 않아, 별도로 DB를 쓰는 API까지 호출해서 확인함.
- **주의**: 검증 전 `docker compose exec fastapi uv run alembic upgrade 20260827_02`를 수동으로 실행해야 했음 — 새 `mysql_volume`엔 테이블이 없었고(`Table 'ai_health.users' doesn't exist`), `docker-compose.yml`엔 자동 마이그레이션이 없음. 이 수동 실행 없이는 DB를 쓰는 모든 API가 500 에러남. 자동화 여부는 위 "volumes 전략 재검토" 항목과 함께 10일차에 같이 검토.

## 향후 개선
- [ ] 목록 API(users, patients, medical-records, predictions)에 pagination 추가 — 각 Day URD에 개별 명시 안 됐지만, 데이터 누적 시 필요

## Day8 이후 해결

| 항목 | 중요도 | 긴급도 | 해결 시점 | 상태 |
|---|---|---|---|---|
| [`Cache-Control: no-store` 추가](#cache-control-no-store-추가) | 높음 | 중간 | day8 커밋 후 별도 bugfix | ⬜ 미착수 |
| 테스트 잔여 계정 정리 검토 | - | - | 팀 확인 후 | ⬜ 미착수 |
| Pydantic 영어 검증 메시지 노출 | 보통 | - | - | ⬜ 미착수 |
| 404 오류 범용 화면 표시 | 보통 | - | - | ⬜ 미착수 |

#### `Cache-Control: no-store` 추가
- 대상: `app/apis/user_apis.py`의 `GET /me` (`app/apis/user.py`는 어디서도 import되지 않는 미사용 코드라 대상 아님)
- 원인 추정: 응답에 캐시 방지 헤더가 없어 브라우저가 URL 기준으로 응답 본문을 캐시함.
- 현재 상태: Day7 실브라우저 테스트 중 같은 브라우저에서 로그아웃 후 다른 계정으로 로그인해도 `/users/me`가 이전 계정 정보를 그대로 반환하는 현상을 2회 재현 확인(2026-09-01). Day7 범위에서는 수정하지 않음.
- 긴급도 재평가(2026-09-03): 현재 프로젝트는 실서비스가 아니고 팀원 간 기기 공유도 없어 긴급도는 중간으로 재평가함. 단, 동일 브라우저에서 계정을 바꾸는 경우 이전 응답이 표시될 수 있으므로 별도 bugfix 대상으로 유지함. 캐시 방지 헤더 자체는 일반적으로 지켜야 할 관행이라 중요도는 유지.
- 해결 방향: 인증된 사용자 정보를 다루는 API 응답(`/users/me` 등)에 `Cache-Control: no-store` 등 캐시 방지 설정 검토. 별도 bugfix commit으로 처리.

#### 테스트 잔여 계정 정리 검토
- 대상(코드/문서/시드 어디에서도 참조되지 않고, 계정명 자체가 단발성 테스트 목적임이 명확한 것만): `signup-test@example.com`(id 5, "회가입테스트"), `final-test@example.com`(id 6, "최종테스트"), `password-test@example.com`(id 7, "비번테스트"), `live-http-check@example.com`(id 24, "라이브HTTP확인").
- `admin123@test.com`(id 12), `testadmin@example.com`(id 14), `user1@example.com`(id 15)는 삭제 대상에서 제외: 실사용 여부를 판단할 근거가 부족함(2026-09-01 조사 결과, 상세는 Day7 대화 기록 참고).
- Day7에서는 삭제하지 않음. 팀 확인 후 대상 확정되면 정리.

#### Pydantic 영어 검증 메시지 노출
- 환자 등록/수정 등 잘못된 입력으로 422가 발생할 때 백엔드의 Pydantic 검증 메시지가 영어 원문 그대로 사용자에게 표시됨. 기능 자체는 정상적으로 422를 반환하고 크래시도 없으므로 UX 개선사항으로 기록. Day7에서 새로 발생한 버그가 아니라 기존 프론트 오류 메시지 처리의 개선사항임.
- 해결 방향: 향후 `apis.js`의 오류 메시지 매핑을 보완하여 사용자 친화적인 한국어 메시지를 표시.

#### 404 오류 범용 화면 표시
- 존재하지 않는 환자/진료기록 ID를 요청하면 백엔드는 정상적으로 404를 반환함. 프론트에서는 현재 범용 오류 카드(예: "찾을 수 없습니다")로 처리되어 구체적인 HTTP 상태나 오류 유형은 표시하지 않음. 크래시나 기능 오류는 아니므로 UX 개선사항으로 기록. 이것 역시 Day7에서 새로 만든 오류 처리 로직이 아니라 기존 프론트 구조의 개선사항임.
- 해결 방향: 향후 필요에 따라 404 등 HTTP 상태별 사용자 메시지를 구분하는 방향으로 개선.

## 근거 문서
- `docs/6일차_폐렴예측_API_설계.md` 4.4장, 11장
