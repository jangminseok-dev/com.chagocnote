# 012 — 예약의 확인할 것·미용 동의·주의 고객 (③-B)

설계 `docs/superpowers/specs/2026-11-14-visit-checks-design.md`. 예약을 잡을 때와 아이를 맞을 때 챙길 것을 자동으로 보이고, 미용 동의를 받은 날과 보호자의 주의 표시를 남긴다. 계획은 둘이다 — ③-B1 백엔드(이 문서의 앞부분), ③-B2 앱.

사용자는 "업계 표준과 꼭 해야 하는 것으로 정해서 진행"하라고 했다. 항목·기준값은 내가 정했고 사용자가 요약을 보고 승인했다. 사용자가 처음부터 확정한 것은 **주의 고객 정보를 매장 사이에 공유하지 않는다**는 것 하나다.

## ③-B1 백엔드에서 정한 것 (2026-11-14)

계획 `docs/superpowers/plans/2026-11-14-visit-3b1-backend.md`. 규칙은 `backend/apps/customer/CLAUDE.md`·`backend/apps/visit/CLAUDE.md` 의 ③-B 단락.

1. **막지 않는다.** 확인할 것은 읽기뿐이고 어떤 쓰기도 거절하지 않는다. "확인했음"을 저장하지 않는다 — 사실이 바뀌면(동의를 받으면, 방문을 마치면) 사라진다.
2. **사실은 customer 의 칸, 판정은 visit 의 순수 함수.** 동의는 `pets` 의 칸 둘, 주의는 `customers` 의 칸 넷(0016). 새 표·새 권한이 없다. visit 은 허브 포트 `CustomerDirectoryPort.care_facts` 로 읽는다.
3. **판정을 `visit/domain/chain/` 에 두지 않았다.** 처음 설계(③-A)가 적어 둔 자리지만, 만든 것은 항목마다 독립으로 내는 함수들이라 책임 연쇄 패턴이 아니다(GoF 이름은 실제 그 패턴일 때만 쓴다). `domain/services/visit_checks.py` 다.
4. **기준일은 방문의 날이다.** 노령(10살)·동의의 유효(365일)·오랜만(180일 초과)을 오늘이 아니라 예약일로 센다.
5. **노쇼는 방문 날 앞 365일만 센다.** 주의 표시가 1년 뒤 풀리는 것과 같다. 상세의 전 기간 `no_show_count` 는 그대로 둔다.
6. **하루 목록의 수는 지병을 세지 않고, 보호자 항목과 아이 항목을 나눠 준다.** 지병은 늘 있는 정보라 세면 표시가 늘 붙는다. 가족 묶음에서 보호자 항목을 한 번만 세게 둘로 나눴다.
7. **지병을 더하면 동의를 비운다.** (종류, 직접 적은 이름)으로 견줘 새 것이 하나라도 있으면 — 기타를 다른 기타로 바꾼 것도. 빼거나 메모만 고친 것은 그대로다. 동의를 받은 뒤 10살이 된 것은 다시 받게 하지 않는다.
8. **기한이 지난 주의는 지우지 않고 읽을 때 거른다.** 상세·목록·확인할 것이 같은 함수(`caution_active`)를 쓴다. 지우는 작업을 따로 돌리지 않는다.
9. **주의 표시는 고객의 `updated_at`(최근순)을 건드리지 않는다.** 고객 정보의 수정이 아니다.
10. **익명화가 주의 칸 넷과 동의 칸 둘을 비운다.**
11. 응답의 확인할 것은 `{code, scope, detail}` 이다 — 코드마다 칸이 달라 펼치지 않았다.
12. 주의·동의의 '오늘'은 customer 의 기존 관례(`seoul_today`)다. 확인할 것의 '오늘'과 방문의 날은 매장 시간대다. 서울 밖의 매장이 생기면 customer 쪽이 하루 어긋날 수 있다(그 스포크 전체가 그렇다).

### 남는 것 — 알고 미룬다

- **첫 방문은 "이 방문의 시작 시각 앞에 시작한 완료 방문이 없다"는 뜻이다**(설계의 문구는 "완료 방문이 하나도 없다"). 지난 채 남은 예약이나, 같은 날 뒤 시각의 예약을 먼저 끝낸 경우에는 "처음 오는 아이"가 계속 뜬다.
- 최종 검토의 Minor(미룸): 통합 테스트의 아이 출생 연도가 고정값(2021)이라 2031년에 노령이 된다 · 통합 테스트·흐름 스크립트가 자정을 걸쳐 돌면 날짜가 어긋날 수 있다 · 호출 수 테스트의 단언 하나가 두 경우를 허용한다 · 익명화 PG 테스트가 다른 매장의 칸이 남았는지는 반려동물·고객 읽기로만 본다 · 동의 받은 날에 하한이 없다(아주 옛 날짜는 기한 지남일 뿐이다) · `detail` 은 스키마의 문 없이 도메인의 키가 그대로 나간다 · 적은 멤버·단 시각 칸은 쓰기만 하고 아직 읽지 않는다.
- 전자 동의서(문안·서명·보호자에게 링크), 예방접종 증명, 예약금·위약금, 기준값을 매장이 바꾸기(설계 2절).
- 주의 표시·동의의 이력이 없다 — 누가 언제 풀었는지 남지 않는다.
- 방문 수정 화면에는 미리 보기가 없다(저장 뒤 상세에 보인다).
- 0016 의 `downgrade` 는 돌려 보지 않았다.
- `VisitCheckPgRepository` 는 물음들을 덮는 범위의 줄을 읽어 메모리에서 나눈다 — 하루 목록의 아이들이 아주 오래 다닌 매장이면 줄이 는다(느려지면 질의 안에서 묶는다).

### ③-B2 앱이 기댈 API 계약

전부 `Authorization: Bearer`, 접두 `/v1/shops/{shop_id}`. 읽기는 매장 멤버면 되고(아니면 403 `NOT_A_MEMBER`), 쓰기 넷은 `customer:write`(사장·직원 모두 있다 — 없으면 403 `PERMISSION_DENIED`). 오류 본문은 `{code, message}`. 날짜는 `YYYY-MM-DD`.

**확인할 것 하나** = `{code, scope, detail}`. `scope` 는 `customer`(보호자 항목) 또는 `pet`(아이 항목). 순서는 서버가 준 그대로 — 주의 · 노쇼 · 첫 방문 · 동의 · 지병 · 오랜만. **모르는 `code` 는 버린다.**

| code | scope | detail |
|---|---|---|
| `caution` | customer | `{reason: str, until: date}` |
| `no_show` | customer | `{count: int}` — 방문 날 앞 365일 |
| `first_visit` | pet | `{}` |
| `consent` | pet | `{reasons: ["senior"·"conditions"…], state: "missing"·"expired", received_on: date·null}` |
| `conditions` | pet | `{items: [{label: str, note: str·null}]}` |
| `long_absence` | pet | `{days: int, last_visit_on: date}` |

- **`GET /visits/{visit_id}`** 에 `checks: [...]` — 예약됨·미용 중인 방문만, 그 밖은 `[]`. 기존 `no_show_count`(전 기간)는 그대로다.
- **`GET /visits?date=`** 의 항목마다 `customer_check_count`·`pet_check_count`(지병은 세지 않는다). 가족 묶음(같은 `group_key`)에서는 `customer_check_count` 를 한 번만 더한다.
- **`GET /visit-checks?customer_id=&pet_ids=&pet_ids=&date=`** → `{customer: [...], pets: [{pet_id, checks: [...]}]}`. `pet_ids` 는 같은 이름을 되풀이한다(0~10개, 없으면 보호자만의 예약). `pets` 는 준 순서대로이고 그 보호자의 아이가 아닌 것은 빠진다. 겹쳐 준 `pet_ids` 는 한 번으로 줄고, 무지개다리 아이는 `checks: []` 로 나온다. **미리 보기의 `no_show.count` 는 그 날의 끝까지, 상세·하루 목록은 그 방문의 시작 시각 앞까지 센다** — 같은 날 앞선 노쇼가 있으면 저장 뒤의 수와 다를 수 있다. 404 `CUSTOMER_NOT_FOUND`(없는·익명화한 고객), 422(11마리, 오늘 앞뒤 366일 밖의 날, 깨진 질의).
- **`PUT /pets/{pet_id}/grooming-consent`** 본문 `{received_on: date|null}`(칸이 없거나 null 이면 오늘, 앞날은 422. **본문 자체는 있어야 한다 — 최소 `{}`**) · **`DELETE`** 같은 경로 → 둘 다 반려동물 상세(쓰기 응답의 모양 — 사진 없음). 404 `PET_NOT_FOUND`.
- **`PUT /customers/{customer_id}/caution`** 본문 `{reason: str}`(앞뒤 공백을 뗀 뒤 1~100자, 한 줄 — 개행·탭 같은 제어 문자가 있으면 422) · **`DELETE`** 같은 경로(없던 것을 풀어도 200) → 둘 다 고객 상세(쓰기 응답의 모양). 404 `CUSTOMER_NOT_FOUND`.
- 더해진 칸: 고객 상세 `customer.caution: {reason, until}|null`, **반려동물 상세 `caution: {reason, until}|null`**(보호자의 것)과 `pet.grooming_consent_on: date|null`, 고객 목록의 줄 `caution: bool`. 기한이 지난 주의는 `null`/`false` 다.

### 검증

2026-11-14 — 단위 2359(기존 2231 + 새 128) · 통합 588(기존 577 + 새 11) · import-linter 6 kept · 라우트 표 94 → 99줄(늘어난 것은 `/caution` 둘·`/grooming-consent` 둘·`/visit-checks` 하나, 없어지거나 바뀐 줄 없음) · 로그인 없는 경로 목록 불변 · 개발 DB 에 0016 올림. `backend/scripts/check_visit_checks_flow.sh` 를 개발 스택(게이트웨이)에서 돌려 32줄 모두 통과했다. 변이 — 기준일을 오늘로, 자기 자신을 이력에 넣기, 기한 지난 주의 거르기 빼기, 지병을 수에 세기, 익명화가 주의를 남기기 — 각각 해당 테스트가 떨어지는 것을 확인했다. 최종 검토(Critical 없음)가 짚은 하나 — 주의 사유에 제어 문자 검증이 없어 NUL 은 500 이 되고 개행은 한 줄 문구를 깨뜨리는 것 — 는 테스트를 먼저 쓰고 고쳤다.
