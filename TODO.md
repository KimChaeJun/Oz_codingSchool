# TODO / 후속 작업

Day별 문서에 흩어놓지 않고, "지금 당장 하지 않기로 한 것"을 전부 여기 한 곳에 모은다.
새로운 후속 작업이 생기면 해당 Day 문서에 근거만 남기고, 실제 TODO는 여기에만 추가한다.

## Docker 단계
- [ ] Alembic 멀티헤드 정리 (`20260826_01` 계보로 통일, `2a635f4b60e5` 폐기)
- [ ] `(record_id, ai_model)` UniqueConstraint 추가
- [ ] `IntegrityError` 처리 (UniqueConstraint 충돌 시 기존 결과 재조회 반환)

## Day7
- [ ] 프론트에서 `heatmap_url: null` 처리 (현재 Hitmap 미생성이라 항상 null)
- [ ] POST `200`/`201` 둘 다 성공으로 처리 (캐시 재사용 시 200)
- [ ] 별도 프론트 서버 사용 시 CORS 설정 필요 여부 확인

## QA
- [ ] 동시 요청 중복 생성 방지 테스트 (Docker 단계 UniqueConstraint 적용 후 재검증)
- [ ] API 전체 응답시간(NFR-PRED-002, 3초 이내) 측정 — DB 조회/파일 I/O/HTTP 포함

## 향후 개선
- [ ] 목록 API(users, patients, medical-records, predictions)에 pagination 추가
      — 각 Day URD에 개별 명시 안 됐지만, 데이터 누적 시 필요

## Day8 이후 해결
- [ ] (Day 8 이후 해결, 우선순위: 높음) `GET /users/me` 응답에 `Cache-Control: no-store` 추가
      — 원인 추정: 응답에 캐시 방지 헤더가 없어 브라우저가 URL 기준으로 응답 본문을 캐시함.
      — 현재 상태: Day7 실브라우저 테스트 중 같은 브라우저에서 로그아웃 후 다른 계정으로 로그인해도
        `/users/me`가 이전 계정 정보를 그대로 반환하는 현상을 2회 재현 확인(2026-09-01). Day7 범위에서는
        수정하지 않음.
      — 해결 방향: 인증된 사용자 정보를 다루는 API 응답(`/users/me` 등)에 `Cache-Control: no-store` 등
        캐시 방지 설정 검토. 다른 사용자에게 이전 로그인 계정 정보가 노출될 수 있는 문제라 우선순위 높음.
- [ ] (Day 8 이후 해결) 테스트 잔여 계정 정리 검토
      — 대상(코드/문서/시드 어디에서도 참조되지 않고, 계정명 자체가 단발성 테스트 목적임이 명확한 것만):
        `signup-test@example.com`(id 5, "회가입테스트"), `final-test@example.com`(id 6, "최종테스트"),
        `password-test@example.com`(id 7, "비번테스트"), `live-http-check@example.com`(id 24, "라이브HTTP확인").
      — `admin123@test.com`(id 12), `testadmin@example.com`(id 14), `user1@example.com`(id 15)는
        삭제 대상에서 제외: 실사용 여부를 판단할 근거가 부족함(2026-09-01 조사 결과, 상세는 Day7 대화 기록 참고).
      — Day7에서는 삭제하지 않음. 팀 확인 후 대상 확정되면 정리.

## 근거 문서
- `docs/6일차_폐렴예측_API_설계.md` 4.4장, 11장
