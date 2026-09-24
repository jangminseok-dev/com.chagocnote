#!/usr/bin/env bash
# 개발 환경에서 사진 발급 → 저장소에 직접 올리기 → 확인 → 기록 쓰기·덧붙이기 → 완료 → 상세·달력·피드·프로필 사진 → 삭제까지
# 게이트웨이와 MinIO 를 거쳐 확인한다. 올리기(PUT)와 읽기(GET)는 서명 URL 로 저장소에 바로 간다.
# 사용: cd infra && docker compose up -d && docker compose run --rm backend python scripts/ensure_media_bucket.py \
#       && bash ../backend/scripts/check_media_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 와 버킷에 확인용 매장·유저·고객·방문·사진이 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }
YESTERDAY="$(at -1 11 | cut -c1-10)"

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# put <URL> <형식> <바이트 수> — 서명 URL 로 저장소에 바로 올린다. 인증 헤더가 없다.
put() { head -c "$3" /dev/zero | curl -s -o /dev/null -w '%{http_code}' -X PUT "$1" -H "Content-Type: $2" --data-binary @-; }
# photo <토큰> — 사진 하나를 발급·올리기·확인까지 마치고 media_id 를 낸다.
photo() {
  local issued; issued=$(call POST "$S/media/uploads" "$1" \
    '{"kind":"photo","content_type":"image/jpeg","byte_size":3000,"width":3000,"height":2000}')
  [ "$(put "$(echo "$issued" | field "['puts']['original']")" image/jpeg 3000)" = 200 ]
  [ "$(put "$(echo "$issued" | field "['puts']['display']")" image/jpeg 800)" = 200 ]
  [ "$(put "$(echo "$issued" | field "['puts']['thumb']")" image/jpeg 200)" = 200 ]
  local id; id=$(echo "$issued" | field "['media_id']")
  [ "$(call POST "$S/media/$id/confirm" "$1" | field "['status']")" = ready ]
  echo "$id"
}

op=$(login "mflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"사진흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "mflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "mflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
echo "통과  매장 $shop_id 에 사장과 직원이 있다"

registered=$(call POST "$S/customers" "$staff_token" "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\
\"pet\":{\"name\":\"콩이\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\
\"weight_kg\":3.2,\"no_known_conditions\":true}}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
# 어제 11시 예약을 시작한다 — 실행 시각과 상관없이 자정을 넘기지 않는다.
visit=$(call POST "$S/visits" "$staff_token" "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at -1 11)\"}" \
  | field "['visits'][0]['visit_id']")
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"start\"}" >/dev/null
R="$S/visits/$visit/record"

early=$(call POST "$S/media/uploads" "$staff_token" '{"kind":"photo","content_type":"image/jpeg","byte_size":3000,"width":3000,"height":2000}')
expect "올리기 전에 확인하면 409" "$(call POST "$S/media/$(echo "$early" | field "['media_id']")/confirm" "$staff_token" | field "['code']")" "MEDIA_NOT_UPLOADED"
expect "서명과 다른 형식은 저장소가 거절" "$(put "$(echo "$early" | field "['puts']['original']")" image/png 10)" "403"
before=$(photo "$staff_token"); after=$(photo "$staff_token")
echo "통과  사진 $before, $after 를 저장소에 바로 올리고 확인했다"

bath=$(call GET "$S/menus" "$staff_token" | field "['items'][0]['menu_id']")
saved=$(call PUT "$R" "$staff_token" "{\"weight_kg\":3.4,\"care_note\":\"눈물 자국 관리\",\"payment_method\":\"card\",\
\"total_amount\":25000,\"items\":[{\"menu_id\":$bath,\"amount\":28000}],\
\"media\":[{\"media_id\":$before,\"phase\":\"before\",\"sort_order\":0}]}")
expect "기록을 처음 쓰면 버전 1" "$(echo "$saved" | field "['version']")" "1"
expect "몸무게가 현재 몸무게가 된다" "$(call GET "$S/pets/$kong" "$staff_token" | field "['pet']['weight_kg']")" "3.4"
appended=$(call POST "$R/media" "$staff_token" "{\"media_id\":$after,\"phase\":\"after\"}")
expect "덧붙이면 버전 2" "$(echo "$appended" | calc "(d['version'], len(d['media']))")" "(2, 2)"
expect "옛 버전으로 저장하면 409" "$(status PUT "$R" "$staff_token" '{"version":1}')" "409"
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"complete\"}" >/dev/null

cover=$(call GET "$S/visits/$visit" "$staff_token" | field "['cover']")
expect "대표 사진은 후 사진" "$(call GET "$S/visits/$visit" "$staff_token" | calc "d['cover'] == [m for m in d['record']['media'] if m['phase'] == 'after'][0]['thumb_url']")" "True"
expect "대표 사진 URL 을 저장소에서 바로 읽는다" "$(curl -s -o /dev/null -w '%{http_code}' "$cover")" "200"
expect "달력 칸의 대표 사진" "$(call GET "$S/visits/calendar?month=${YESTERDAY:0:7}" "$staff_token" \
  | calc "[x['cover'] for x in d['days'] if x['date'] == '$YESTERDAY'][0] == '$cover'")" "True"
expect "피드 카드" "$(call GET "$S/visits/feed?pet_id=$kong" "$staff_token" | calc "(d['items'][0]['visit_id'], d['items'][0]['media_count'])")" "($visit, 2)"
expect "반려동물 프로필 사진" "$(call GET "$S/pets/$kong" "$staff_token" | calc "d['pet']['photo'] == '$cover'")" "True"

expect "직원은 기록을 지우지 못한다" "$(status DELETE "$R" "$staff_token")" "403"
expect "사장은 기록을 지운다" "$(status DELETE "$R" "$owner_token")" "204"
expect "기록이 없으면 대표 사진도 없다" "$(call GET "$S/visits/$visit" "$staff_token" | calc "(d['record'], d['cover'])")" "(None, None)"

echo "전체 흐름 확인 완료"
