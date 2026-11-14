#!/usr/bin/env bash
# 개발 환경에서 기록 검색 흐름을 게이트웨이를 거쳐 확인한다(⑨-1a) — 기록을 적으면 잠시 뒤 글자로 찾아진다 → 말을 바꿔도
# 찾아진다(뜻 검색) → 지병 이름으로 찾아진다 → 아이로 좁힌다 → 기록을 지우면 사라진다 → 고객을 익명화하면 곧바로 사라진다 →
# 다른 매장에서는 안 보인다 → 검색어가 짧으면 422 → 임베딩 프로세스를 멈춰도 글자 검색은 200.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_search_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정과 embed 멈춤·시작을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문이 남는다.
# 단계 이름과 판정만 찍는다 — 검색어·걸린 문장·응답 본문·토큰·전화번호는 찍지 않는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE_A="010$(printf '%08d' $((STAMP % 100000000)))"
PHONE_B="010$(printf '%08d' $(((STAMP + 1) % 100000000)))"
PHONE_C="010$(printf '%08d' $(((STAMP + 2) % 100000000)))"
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
at() { echo "$(day "$1")T$(printf '%02d' "$2"):00:00+09:00"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# search <매장 경로> <토큰> <검색어> [pet_id] — 응답 JSON. 검색어는 주소에 %XX 로 실린다.
search() { curl -s -G "$BASE$1/search" -H "Authorization: Bearer $2" --data-urlencode "q=$3" ${4:+--data-urlencode "pet_id=$4"}; }
search_status() { curl -s -o /dev/null -w '%{http_code}' -G "$BASE$1/search" -H "Authorization: Bearer $2" --data-urlencode "q=$3"; }
count() { python3 -c "import json,sys; print(len(json.load(sys.stdin)['items']))"; }
# of_customer <고객ID> — 그 고객의 줄 수. of_visit <방문ID> <kind> — 그 방문의 그 종류 줄 수.
# 뜻 검색은 맞는 글이 없어도 "가장 가까운 글" 몇 개(최대 10)를 준다 — 그래서 "사라졌다"는 줄 수가 아니라 그 글이 없는지로 본다.
of_customer() { python3 -c "import json,sys; print(sum(1 for i in json.load(sys.stdin)['items'] if i['owner']['customer_id'] == $1))"; }
of_visit() { python3 -c "import json,sys; print(sum(1 for i in json.load(sys.stdin)['items'] if i['visit_id'] == $1 and i['kind'] == '$2'))"; }
# until_gone <매장 경로> <토큰> <검색어> <방문ID> <kind> — 그 방문의 그 글이 검색에서 빠질 때까지 기다린다(15초까지).
until_gone() {
  local n=""
  for _ in $(seq 1 30); do
    n=$(search "$1" "$2" "$3" | of_visit "$4" "$5")
    [ "$n" = "0" ] && break
    sleep 0.5
  done
  echo "$n"
}
# until_found <매장 경로> <토큰> <검색어> <방문ID> <kind> — 그 방문의 그 글이 검색에 들 때까지 기다린다(15초까지).
until_found() {
  local n=""
  for _ in $(seq 1 30); do
    n=$(search "$1" "$2" "$3" | of_visit "$4" "$5")
    [ "$n" = "1" ] && break
    sleep 0.5
  done
  echo "$n"
}
# until_count <기대 줄 수> <매장 경로> <토큰> <검색어> — 색인기를 기다린다(15초까지). 마지막 줄 수를 찍는다.
until_count() {
  local n=""
  for _ in $(seq 1 30); do
    n=$(search "$2" "$3" "$4" | count)
    [ "$n" = "$1" ] && break
    sleep 0.5
  done
  echo "$n"
}

# 1. 매장 둘
op=$(login "sflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
open_shop() {   # <이름> <사장 로그인 이름> — "매장ID 사장토큰"
  local req="{\"name\":\"$1\"}" shop code owner accept
  shop=$(call POST /v1/platform/shops "$op_token" "$req")
  code=$(echo "$shop" | field "['owner_invite_code']")
  owner=$(login "$2" | field "['access_token']")
  accept="{\"code\":\"$code\"}"
  call POST /v1/invites/accept "$owner" "$accept" >/dev/null
  echo "$(echo "$shop" | field "['shop_id']") $owner"
}
read -r shop_id owner <<<"$(open_shop "검색흐름-$STAMP" "sflow-owner-$STAMP")"
read -r other_shop other_owner <<<"$(open_shop "검색흐름B-$STAMP" "sflow-other-$STAMP")"
S="/v1/shops/$shop_id"; B="/v1/shops/$other_shop"

# family <이름> <번호> <아이 이름> <특이사항> <지병 JSON 배열> <보호자 메모> — "고객ID 아이ID"
family() {
  local none=true; [ "$5" = "[]" ] || none=false
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":false,\"memo\":\"$6\"},\"pet\":{\"name\":\"$3\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":$none,\"conditions\":$5,\"memo\":\"$4\"}}"
  call POST "$S/customers" "$owner" "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customer']['customer_id'], d['pets'][0]['pet_id'])"
}
HEART='{"type_code":"heart_disease","custom_label":null,"note":"약 복용 중"}'
read -r kong_owner kong <<<"$(family 김민지 "$PHONE_A" 콩이 "드라이기 소리를 무서워해요" "[$HEART]" "미용이 끝나면 전화를 달라고 하심")"
read -r dubu_owner dubu <<<"$(family 이수진 "$PHONE_B" 두부 "드라이기 소리를 무서워해요" "[]" "")"

# 2. 어제 방문에 기록을 적는다
visit_req="{\"customer_id\":$kong_owner,\"pet_ids\":[$kong],\"starts_at\":\"$(at -1 11)\",\"memo\":\"발톱을 짧게 깎아 달라고 하심\"}"
visit_id=$(call POST "$S/visits" "$owner" "$visit_req" | field "['visits'][0]['visit_id']")
start_req="{\"visit_ids\":[$visit_id],\"action\":\"start\"}"
call POST "$S/visits/transitions" "$owner" "$start_req" >/dev/null
record_req='{"care_note":"귀 청소할 때 예민하게 반응했어요. 귀 안쪽을 만지면 고개를 심하게 털어요.","internal_note":"입 주변을 만지면 무는 시늉을 함"}'
expect "기록을 적는다" "$(status PUT "$S/visits/$visit_id/record" "$owner" "$record_req")" "200"

# 3. 잠시 뒤 글자로 찾아진다
expect "잠시 뒤 글자로 찾아진다" "$(until_found "$S" "$owner" "귀 청소할 때" "$visit_id" care_note)" "1"
found=$(search "$S" "$owner" "귀 청소할 때")
expect "그 글이 맨 위이고, 줄은 그 방문으로 가며 아이 이름과 방문 날이 실린다" "$(echo "$found" | python3 -c "import json,sys; i=json.load(sys.stdin)['items'][0]; print(i['kind'], i['visit_id'], i['pet']['name'], i['date'], i['open_pet_id'])")" "care_note $visit_id 콩이 $(day -1) None"
expect "같은 방문의 글 셋이 걸려도 한 줄이다" "$(search "$S" "$owner" "만지면" | python3 -c "import json,sys; print(sum(1 for i in json.load(sys.stdin)['items'] if i['visit_id'] == $visit_id))")" "1"

# 4. 말을 바꿔도 찾아진다 — 글자는 겹치지 않는다
meaning=$(search "$S" "$owner" "드라이어 바람에 겁먹는 강아지")
expect "뜻 검색이 함께 됐다" "$(echo "$meaning" | field "['semantic']")" "True"
expect "말을 바꿔도 그 아이의 특이사항이 걸린다" "$(echo "$meaning" | python3 -c "import json,sys; print(any(i['kind'] == 'pet_memo' and i['open_pet_id'] == $kong for i in json.load(sys.stdin)['items']))")" "True"

# 5. 지병 이름과 보호자 메모
expect "지병 이름으로 찾으면 맨 위에 오고 그 아이를 연다" "$(search "$S" "$owner" "심장 질환" | python3 -c "import json,sys; i=json.load(sys.stdin)['items'][0]; print(i['kind'], i['open_pet_id'], i['visit_id'])")" "condition_note $kong None"
expect "보호자 메모는 아이 없이 보호자 이름으로, 열 아이와 함께" "$(search "$S" "$owner" "전화를 달라고" | python3 -c "import json,sys; i=json.load(sys.stdin)['items'][0]; print(i['kind'], i['pet'], i['owner']['name'], i['open_pet_id'])")" "customer_memo None 김민지 $kong"

# 6. 아이로 좁힌다
expect "매장 전체에서는 두 아이가 다 걸린다" "$(search "$S" "$owner" "드라이기" | python3 -c "import json,sys; print(sorted({i['pet']['name'] for i in json.load(sys.stdin)['items'] if i['kind'] == 'pet_memo'}))")" "['두부', '콩이']"
expect "아이로 좁히면 그 아이의 글만" "$(search "$S" "$owner" "드라이기" "$dubu" | python3 -c "import json,sys; print(sorted({(i['pet'] or {}).get('name') for i in json.load(sys.stdin)['items']}))")" "['두부']"

# 7. 다른 매장
expect "다른 매장의 사장은 이 매장을 찾지 못한다(403)" "$(search_status "$S" "$other_owner" "드라이기")" "403"
expect "다른 매장에서는 한 줄도 안 보인다" "$(search "$B" "$other_owner" "드라이기" | count)" "0"
expect "다른 매장에서 이 매장의 아이로 좁혀도 없다" "$(search "$B" "$other_owner" "드라이기" "$kong" | count)" "0"

# 8. 검색어 규칙
expect "한 글자 검색어는 422" "$(search_status "$S" "$owner" "귀")" "422"
expect "422 본문에 검색어가 없다" "$(search "$S" "$owner" "귀" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['code'], '귀' in d['message'])")" "VALIDATION_ERROR False"

# 9. 기록을 지우면 사라진다
expect "기록을 지운다" "$(status DELETE "$S/visits/$visit_id/record" "$owner")" "204"
expect "잠시 뒤 그 케어 노트가 검색에서 사라진다" "$(until_gone "$S" "$owner" "귀 청소" "$visit_id" care_note)" "0"
expect "내부 메모도 사라진다" "$(search "$S" "$owner" "무는 시늉" | of_visit "$visit_id" internal_note)" "0"
expect "예약 메모는 남아 있다" "$(search "$S" "$owner" "발톱을 짧게" | of_visit "$visit_id" visit_memo)" "1"

# 10. 익명화하면 기다리지 않아도 사라진다
done_req="{\"visit_ids\":[$visit_id],\"action\":\"complete\"}"
call POST "$S/visits/transitions" "$owner" "$done_req" >/dev/null
expect "고객을 익명화한다" "$(status DELETE "$S/customers/$kong_owner" "$owner")" "204"
expect "곧바로 그 고객의 글이 없다 — 특이사항" "$(search "$S" "$owner" "드라이기" | of_customer "$kong_owner")" "0"
expect "곧바로 그 고객의 글이 없다 — 예약 메모·지병·보호자 메모" "$(search "$S" "$owner" "발톱을 짧게" | of_customer "$kong_owner") $(search "$S" "$owner" "심장 질환" | of_customer "$kong_owner") $(search "$S" "$owner" "전화를 달라고" | of_customer "$kong_owner")" "0 0 0"

# 11. 임베딩 프로세스를 멈춰도 글자 검색은 된다
trap 'docker compose start embed >/dev/null 2>&1' EXIT   # 중간에 실패해도 embed 를 멈춘 채 두지 않는다
docker compose stop embed >/dev/null 2>&1
down=$(search "$S" "$owner" "드라이기")
expect "임베딩이 멈춰도 200 이고 글자로 찾는다" "$(search_status "$S" "$owner" "드라이기") $(echo "$down" | count)" "200 1"
expect "뜻 검색은 꺼진 것으로 알린다" "$(echo "$down" | field "['semantic']")" "False"
read -r late_owner late <<<"$(family 박지호 "$PHONE_C" 보리 "빗질할 때 얌전해요" "[]" "")"
expect "임베딩이 멈춰 있어도 새 글이 글자로 찾아진다" "$(until_count 1 "$S" "$owner" "빗질할 때")" "1"
docker compose start embed >/dev/null 2>&1
for _ in $(seq 1 60); do
  docker compose exec -T backend python -c "import httpx; httpx.get('http://embed:8100/health', timeout=2).raise_for_status()" >/dev/null 2>&1 && break
  sleep 1
done
expect "임베딩이 돌아오면 다시 뜻 검색이 된다" "$(search "$S" "$owner" "드라이기" | field "['semantic']")" "True"
echo "기록 검색 흐름 확인 끝 (매장 ${shop_id}, 확인용 고객 ${dubu_owner}·${late_owner} 가 남는다)"
