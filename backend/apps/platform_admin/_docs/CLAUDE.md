# platform_admin — 플랫폼 운영자 표면

소유 데이터: 없음. 허브 포트만 쓴다.

- 모든 라우터는 `dependencies=[Depends(require_operator)]`로 운영자 가드를 건다. 빠뜨리면 `tests/`의 구조 테스트가 실패한다. 유스케이스에서는 운영자를 다시 확인하지 않는다.
- 운영자가 아니면 `NotAnOperatorError`(403, `PERMISSION_DENIED`)다.
- 매장 개설은 tenancy가 구현한 `ShopProvisioningPort`로 한다. 이 스포크는 매장 테이블을 모른다.
- 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
