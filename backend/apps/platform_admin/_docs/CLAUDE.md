# platform_admin — 플랫폼 운영자 표면

소유 데이터: 없음. 허브 포트만 쓴다.

- 모든 유스케이스는 첫 줄에서 `OperatorDirectoryPort.is_operator`를 확인한다. 가드 의존성으로 빼지 않는다. 확인을 빠뜨린 슬라이스가 스텁 테스트에서 드러나게 하려는 것이다.
- 운영자가 아니면 `NotAnOperatorError`(403, `PERMISSION_DENIED`)다.
- 매장 개설은 tenancy가 구현한 `ShopProvisioningPort`로 한다. 이 스포크는 매장 테이블을 모른다.
- 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
