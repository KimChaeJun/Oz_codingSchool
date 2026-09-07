import os

# 로컬/CI에서 실행 중인 실제 Docker ai-worker(REDIS_DB=0)와 pytest의 자체
# 워커 스레드가 같은 Redis 큐를 두고 경쟁하면 테스트가 비결정적으로
# 실패한다 (실제로 한 번 재현됨). 테스트는 별도 DB 번호를 강제해 완전히
# 분리한다 — 셸에 이미 REDIS_DB가 설정돼 있어도(예: 개발자가 Docker와
# 맞추려고 REDIS_DB=0을 export해둔 경우) 테스트는 항상 격리된 DB를 써야
# 하므로 setdefault가 아니라 강제 대입한다.
# app.core.config.Settings()가 인스턴스화되기 전에(즉 다른 테스트 모듈이
# app을 import하기 전에) 반드시 먼저 실행돼야 하므로, conftest.py
# 최상단에 둔다 — pytest는 각 디렉터리의 conftest.py를 그 안의 테스트
# 모듈보다 먼저 import한다.
os.environ["REDIS_DB"] = "1"
