# 011 — 매출 통계 (⑧)

설계 `docs/superpowers/specs/2026-11-14-sales-design.md`. 사장이 홈의 [매출] 탭에서 기간의 매출을 보고 다시 올 때가 지난 아이를 챙긴다. 계획은 셋이다 — ⑧-1 백엔드(이 문서의 앞부분), ⑧-2 앱 매출 탭, ⑧-3 앱의 이어지는 화면.

## ⑧-1 백엔드에서 정한 것 (2026-11-14)

계획 `docs/superpowers/plans/2026-11-14-sales-8-1-backend.md`. 규칙은 `backend/apps/visit/_docs/CLAUDE.md` 의 매출 단락.

1. **새 스포크를 만들지 않았다.** 집계는 `visit` 의 읽기 슬라이스 넷과 쓰기 슬라이스 하나다. 경로는 `/v1/shops/{shop_id}/sales/…`, 전부 `sales:read`(사장만 — 기반 설계). 목표 정하기도 같은 권한이다(새 권한 없음).
2. **집계는 읽을 때 SQL 로 한다.** 미리 계산한 표·캐시·배치가 없다. 작은 매장의 한 해 방문은 수천 줄이다. 느려지면 그때 날짜별 합을 따로 둔다.
3. **방문한 날 기준 하나**(시작 시각이 든 날, 매장 시간대). 받은 날 기준은 없다.
4. **총액이 없는 완료 방문은 0 이 아니라 빠진 것**으로 따로 센다. 통계가 비어 보이는 가장 흔한 까닭이 입력 누락이라 화면이 그 수를 보이고 채우러 가게 한다.
5. **조정·미선택 줄로 합을 맞춘다.** 결제 수단 합 = 메뉴 합 + 조정 = 칸의 합 = 매출.
6. **진행 중인 기간은 같은 길이만큼만 견준다.** 작년 줄은 작년에 매출이 있었을 때만.
7. **아이의 사진은 프로필 사진**(가장 최근 대표)이다. 방문마다의 대표를 쓰면 요약 하나에 기록 수백 개를 읽어야 한다. 고른 날 카드의 사진이 그날 찍은 사진이 아닐 수 있다 — 누르면 가는 하루 화면에는 그날 사진이 보인다.
8. **익명화한 고객의 아이와 지운 아이는 합계에 남고 얼굴에서 빠진다.** 무지개다리를 건넌 아이는 다녀간 얼굴·단골에는 나오고 다시 올 때가 지난 아이에서만 빠진다.
9. **다시 올 때가 지난 아이는 8주(56일)~1년, 고정값.** 미용 중인 아이는 "앞으로의 예약이 있는 것"으로 친다.
10. **월 목표는 설정 행의 한 칸**이고 이번 달의 월 보기에만 실린다. 이력을 두지 않았다.
11. **남은 예약의 예상 금액은 정가 합**이다. 설계 단계에서 "메뉴에 기본 가격이 없다"고 사용자에게 잘못 말했다 — 구현 중에 `service_menus.price` 를 보고 바로잡아 넣었다.
12. **알림장의 "보냈다"는 한 번이라도 만든 적이 있다는 뜻**이다.
13. 단골은 보고 있는 기간의 지나간 마지막 날이 든 해(오늘까지)에서 고른다.

### 알려진 동작 — 막지 않기로 했다

- 방문을 완료한 뒤 날짜(시작 시각)를 고치면 매출이 든 날이 함께 옮겨 간다 — 방문한 날 기준이라서다.
- 기록의 총액을 0 으로 적으면 "금액을 적은 방문"이고 평균을 낮춘다(무료 서비스).
- 다시 올 때가 지난 아이의 목록은 후보를 다 읽고 메모리에서 쪽을 나눈다(후보는 지난 한 해에 온 아이). 아이가 수만이 되면 저장소에서 나눠야 한다.
- 요약 한 번에 저장소 질의가 열 번 남짓, 허브 포트 호출이 서너 번이다. 연 보기는 날짜별 365줄을 읽어 달로 접는다.
- 해를 걸친 주의 단골은 뒤쪽 해 기준이다.

### 남는 것 — 알고 미룬다

- 직원별 매출(담당 미용사가 없다), 엑셀·CSV, 부가세·현금영수증, 외상·선결제·환불, 시간대별, 업계 평균, 주간 요약 알림, 임의 기간, 달마다 다른 목표, 8주 기준 바꾸기(설계 6절).
- 0015 의 `downgrade` 는 돌려 보지 않았다.

### ⑧-2·⑧-3 앱이 기댈 API 계약

전부 `Authorization: Bearer`, 접두 `/v1/shops/{shop_id}/sales`, `sales:read` 가 없으면 403 `PERMISSION_DENIED`, 멤버가 아니면 403 `NOT_A_MEMBER`. 오류 본문은 `{code, message}`. 금액은 정수(원), 날짜는 `YYYY-MM-DD`(매장 시간대).

**`GET /summary?span=day|week|month|year&anchor=YYYY-MM-DD`** — `anchor` 는 그 기간 안의 아무 날(없으면 매장의 오늘, 받는 범위 2000-01-01~2100-12-31). 앞날의 기간은 빈 요약(200)이다.

```
span
period{start, end, elapsed_end|null}                 # end 는 끝날(포함). elapsed_end 는 지나간 마지막 날 — 앞날의 기간이면 null
revenue, visit_count, priced_count, average|null      # average = revenue // priced_count
compare{previous{start,end,revenue}|null, year_ago{start,end,revenue}|null}
goal{monthly_amount}|null                             # 이번 달의 월 보기 + 목표가 있을 때만
pets{count, new_count, returning_count, faces[PetCard≤6], new[PetCard≤3], returning[PetCard≤4]}
buckets[{key, revenue, visit_count, future, pets[PetCard≤5]}]   # 주·월은 날마다("YYYY-MM-DD"), 연은 달마다("YYYY-MM", pets 는 빈 목록), 일은 빈 목록
payments[{method: card|cash|transfer|none, amount}]   # 0원인 줄 없음, 이 순서
menus[{menu_id|null, name, amount, count, pet: PetCard|null}]   # 금액순. 조정 줄은 menu_id null·name "조정"·count 0, 금액이 음수일 수 있다
regulars[{pet: PetCard, visit_count}]                 # 셋까지
bookings{remaining|null, expected_amount|null, no_show, canceled}   # remaining 은 진행 중인 기간에만. expected_amount 는 정가 합(없으면 null)
weekdays[7 ints, 월~일]|null                          # 월·연 보기에만
report{completed, sent, opened}|null                  # 완료 방문이 0 이면 null
unrecorded_count, due_pet_count
```

`PetCard` = `{pet_id, name, photo_url|null}`. `photo_url` 은 서명 주소(썸네일)다 — 저장하지 않는다.

**`GET /visits?span=&anchor=&filter=unrecorded|no_show|canceled|menu&menu_id=&cursor=`** → `{items: [{visit_id, date, pet: PetCard|null, amount: int|null}], next_cursor}` 최신순 20개. `filter=menu` 면 `menu_id` 필수(없으면 422). 남의 매장·없는 메뉴는 빈 목록. `pet` 은 보호자만의 방문·익명화·지운 아이면 null(방문은 보인다).

**`GET /due-pets?cursor=`** → `{items: [{pet: PetCard, last_visit_date}], next_cursor}` 오래된 순 20개. 요약의 `due_pet_count` 와 같은 거르기다.

**`GET /goal`** → `{monthly_amount: int|null}`. **`PUT /goal`** 본문 `{monthly_amount: int|null}`(0~100,000,000, 0·null 은 지우기) → 같은 모양.

422: 없는 `span`·`filter`, 날짜가 아닌·범위 밖 `anchor`, 깨진 `cursor`, 범위 밖 `menu_id`, 목표의 음수·소수·문자열.

### 흐름 확인

2026-11-14 — 단위 2231(기존 2032 + 새 199) · 통합 577(기존 541 + 새 36) · import-linter 6 kept · 라우트 표 89 → 94줄(늘어난 것은 `/sales/…` 다섯, 없어지거나 바뀐 줄 없음) · 로그인 없는 경로 목록 불변 · 개발 DB 에 0015 올림. `backend/scripts/check_sales_flow.sh` 를 개발 스택(게이트웨이)에서 돌려 여덟 단계·확인 33줄 모두 통과했다. 판별력: 평균의 기대를 33334 로 바꾸면 그 줄에서 멈춘다. 기존 `check_visit_flow.sh`(31줄)·`check_report_flow.sh`(34줄)·`check_guardian_flow.sh`(30줄)도 그대로 통과했다. 변이 — 날짜를 시간대 없이 자르기, 기간 경계를 UTC 자정으로, 매장 조건 빼기, 메뉴에서 총액 NULL 조건 빼기, 익명화 거르기 빼기, 조정 줄 빼기, 비교를 앞 기간 전체로, 무지개다리 거르기 빼기, 한 줄 더 읽지 않기, 쪽 경계를 포함으로 — 각각 해당 테스트가 떨어지는 것을 확인했다.
