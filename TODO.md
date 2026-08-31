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

## 근거 문서
- `docs/6일차_폐렴예측_API_설계.md` 4.4장, 11장
