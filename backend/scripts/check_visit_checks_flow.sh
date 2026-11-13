#!/usr/bin/env bash
# 개발 환경에서 "확인할 것"·미용 동의·주의 표시 흐름을 게이트웨이를 거쳐 확인한다(③-B) — 노령·지병 아이를 내일 예약하면
# 방문 상세에 첫 방문·동의·지병이 뜬다 → 동의를 받았다고 적으면 동의가 사라진다 → 지병을 더하면 다시 뜬다 →
# 다른 보호자의 어제 완료·그저께 노쇼 뒤 내일 예약에는 노쇼만 → 직원이 주의를 달면 주의가 더해지고 하루 목록의 수·고객 목록·
# 반려동물 상세에 보인다 → 미리 보기(아직 없는 예약) → 풀면 사라진다 → 확인할 것이 있어도 시작·완료가 된다 → 다른 매장은 404.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_visit_checks_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문이 남는다.
# 단계 이름과 판정만 찍는다 — 주의 사유·전화번호·토큰은 찍지 않는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE_A="010$(printf '%08d' $((STAMP % 100000000)))"
PHONE_B="010$(printf '%08d' $(((STAMP + 1) % 100000000)))"
day() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; print(d.date.today()+d.timedelta(days=int(sys.argv[1])))" "$1"; }
at() { echo "$(day "$1")T$(printf '%02d' "$2"):00:00+09:00"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# codes — 방문 상세의 확인할 것 코드를 쉼표로.
codes() { python3 -c "import json,sys; print(','.join(c['code'] for c in json.load(sys.stdin)['checks']))"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
# 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
login() { local body="{\"provider\":\"dev\",\"token\":\"$1\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

TODAY="$(day 0)"; TOMORROW="$(day 1)"

# 1. 매장·사장·직원
op=$(login "cflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"확인흐름-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner=$(login "cflow-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
staff_code=$(call POST "$S/invites" "$owner" | field "['code']")
staff=$(login "cflow-staff-$STAMP" | field "['access_token']")
staff_req="{\"code\":\"$staff_code\"}"
call POST /v1/invites/accept "$staff" "$staff_req" >/dev/null

# pet_body <이름> <출생 연도> <지병 JSON 배열> — 반려동물 본문
pet_body() {
  local none=true; [ "$3" = "[]" ] || none=false
  echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":$2,\"weight_kg\":3.2,\"no_known_conditions\":$none,\"conditions\":$3}"
}
# family <이름> <번호> <반려동물 본문> — "고객ID 아이ID"
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":$3}"
  call POST "$S/customers" "$owner" "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['customer']['customer_id'], d['pets'][0]['pet_id'])"
}
visit() { local body="{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$3\"}"; call POST "$S/visits" "$owner" "$body" | field "['visits'][0]['visit_id']"; }
move() { local body="{\"visit_ids\":[$1],\"action\":\"$2\"}"; status POST "$S/visits/transitions" "$owner" "$body"; }

HEART='{"type_code":"heart_disease","custom_label":null,"note":"약 복용 중"}'
ALLERGY='{"type_code":"allergy","custom_label":null,"note":null}'
OLD_YEAR=$(( $(TZ=Asia/Seoul date +%Y) - 15 ))
read -r old_owner old_pet <<<"$(family 김노령 "$PHONE_A" "$(pet_body 초코 "$OLD_YEAR" "[$HEART]")")"
read -r kong_owner kong <<<"$(family 박콩이 "$PHONE_B" "$(pet_body 콩이 "$(( OLD_YEAR + 12 ))" "[]")")"

# 2. 노령·지병 아이의 내일 예약 — 첫 방문·동의·지병
v_old=$(visit "$old_owner" "$old_pet" "$(at 1 11)")
expect "노령·지병 아이의 첫 예약 — 첫 방문·동의·지병" "$(call GET "$S/visits/$v_old" "$owner" | codes)" "first_visit,consent,conditions"
expect "동의는 '없음'이고 까닭은 노령·지병" "$(call GET "$S/visits/$v_old" "$owner" | python3 -c "import json,sys; d=[c for c in json.load(sys.stdin)['checks'] if c['code']=='consent'][0]['detail']; print(d['state'], ','.join(d['reasons']))")" "missing senior,conditions"

# 3. 동의를 받았다고 적으면 사라지고, 지병을 더하면 다시 뜬다
expect "동의 받음 — 받은 날은 오늘" "$(call PUT "$S/pets/$old_pet/grooming-consent" "$owner" '{}' | field "['pet']['grooming_consent_on']")" "$TODAY"
expect "동의를 받으면 동의 항목이 사라진다" "$(call GET "$S/visits/$v_old" "$owner" | codes)" "first_visit,conditions"
more="$(pet_body 초코 "$OLD_YEAR" "[$HEART,$ALLERGY]")"
expect "지병을 더하면 받아 둔 동의가 비워진다" "$(call PUT "$S/pets/$old_pet" "$owner" "$more" | field "['pet']['grooming_consent_on']")" "None"
expect "다시 동의 항목이 뜬다" "$(call GET "$S/visits/$v_old" "$owner" | codes)" "first_visit,consent,conditions"
future="{\"received_on\":\"$TOMORROW\"}"
expect "앞날의 동의는 422" "$(status PUT "$S/pets/$old_pet/grooming-consent" "$owner" "$future")" "422"

# 4. 어제 완료·그저께 노쇼인 보호자의 내일 예약 — 노쇼만
v_done=$(visit "$kong_owner" "$kong" "$(at -1 10)"); move "$v_done" start >/dev/null; move "$v_done" complete >/dev/null
v_miss=$(visit "$kong_owner" "$kong" "$(at -2 10)"); move "$v_miss" no_show >/dev/null
v_next=$(visit "$kong_owner" "$kong" "$(at 1 14)")
expect "어제 다녀간 아이의 다음 예약 — 노쇼만" "$(call GET "$S/visits/$v_next" "$owner" | codes)" "no_show"
expect "완료한 방문에는 확인할 것이 없다" "$(call GET "$S/visits/$v_done" "$owner" | codes)" ""

# 5. 직원이 주의를 단다
caution_req='{"reason":"  흐름 확인용 사유  "}'
expect "직원이 주의 표시를 단다" "$(status PUT "$S/customers/$kong_owner/caution" "$staff" "$caution_req")" "200"
expect "끝나는 날은 365일 뒤" "$(call GET "$S/customers/$kong_owner" "$owner" | field "['customer']['caution']['until']")" "$(day 365)"
expect "사유는 앞뒤 공백을 떼고 저장된다(길이만 본다)" "$(call GET "$S/customers/$kong_owner" "$owner" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['customer']['caution']['reason']))")" "9"
expect "예약의 확인할 것에 주의가 더해진다" "$(call GET "$S/visits/$v_next" "$staff" | codes)" "caution,no_show"
expect "하루 목록 — 보호자 항목 2, 아이 항목 0 / 노령 아이는 0, 2" "$(call GET "$S/visits?date=$TOMORROW" "$owner" | python3 -c "import json,sys; print(' '.join('%d:%d' % (i['customer_check_count'], i['pet_check_count']) for i in json.load(sys.stdin)['items']))")" "0:2 2:0"
expect "고객 목록에는 여부만 있다" "$(call GET "$S/customers" "$owner" | python3 -c "import json,sys; d=json.load(sys.stdin)['items']; print(sorted(str(i['caution']) for i in d), any('reason' in i for i in d))")" "['False', 'True'] False"
expect "반려동물 상세에 보호자의 주의가 실린다" "$(call GET "$S/pets/$kong" "$owner" | field "['caution']['until']")" "$(day 365)"

# 6. 미리 보기 — 아직 없는 예약
preview=$(call GET "$S/visit-checks?customer_id=$kong_owner&pet_ids=$kong&date=$(day 3)" "$staff")
expect "미리 보기 — 보호자 항목은 주의·노쇼, 아이 항목은 없음" "$(echo "$preview" | python3 -c "import json,sys; d=json.load(sys.stdin); print(','.join(c['code'] for c in d['customer']), len(d['pets'][0]['checks']))")" "caution,no_show 0"
expect "미리 보기 — 남의 아이는 빠진다" "$(call GET "$S/visit-checks?customer_id=$kong_owner&pet_ids=$old_pet&date=$(day 3)" "$owner" | field "['pets']")" "[]"
expect "미리 보기 — 없는 고객은 404" "$(status GET "$S/visit-checks?customer_id=999999999&date=$(day 3)" "$owner")" "404"
expect "미리 보기 — 예약 범위 밖의 날은 422" "$(status GET "$S/visit-checks?customer_id=$kong_owner&date=$(day 400)" "$owner")" "422"

# 7. 풀면 사라진다
expect "직원이 주의를 푼다" "$(status DELETE "$S/customers/$kong_owner/caution" "$staff")" "200"
expect "풀고 나면 노쇼만 남는다" "$(call GET "$S/visits/$v_next" "$owner" | codes)" "no_show"
expect "없는 것을 풀어도 200" "$(status DELETE "$S/customers/$kong_owner/caution" "$owner")" "200"

# 8. 막지 않는다 — 확인할 것이 있는 오늘의 예약도 시작·완료된다
v_today=$(visit "$old_owner" "$old_pet" "$(at 0 9)")
expect "확인할 것이 셋인 예약" "$(call GET "$S/visits/$v_today" "$owner" | codes)" "first_visit,consent,conditions"
expect "시작된다" "$(move "$v_today" start)" "200"
expect "미용 중에도 보인다" "$(call GET "$S/visits/$v_today" "$owner" | codes)" "first_visit,consent,conditions"
expect "완료된다" "$(move "$v_today" complete)" "200"
expect "완료하면 없다" "$(call GET "$S/visits/$v_today" "$owner" | codes)" ""
expect "그 뒤의 내일 예약은 더는 첫 방문이 아니다" "$(call GET "$S/visits/$v_old" "$owner" | codes)" "consent,conditions"

# 9. 다른 매장은 닿지 못한다
shop2_req="{\"name\":\"확인흐름2-$STAMP\"}"
shop2=$(call POST /v1/platform/shops "$op_token" "$shop2_req")
shop2_id=$(echo "$shop2" | field "['shop_id']"); code2=$(echo "$shop2" | field "['owner_invite_code']")
other=$(login "cflow-other-$STAMP" | field "['access_token']")
accept2="{\"code\":\"$code2\"}"
call POST /v1/invites/accept "$other" "$accept2" >/dev/null
expect "다른 매장 — 자기 매장 경로로 남의 고객에 주의 달기는 404" "$(status PUT "/v1/shops/$shop2_id/customers/$kong_owner/caution" "$other" "$caution_req")" "404"
expect "다른 매장 — 남의 매장 경로는 403" "$(status PUT "$S/customers/$kong_owner/caution" "$other" "$caution_req")" "403"
expect "다른 매장 — 남의 아이에 동의 적기는 404" "$(status PUT "/v1/shops/$shop2_id/pets/$old_pet/grooming-consent" "$other" '{}')" "404"
echo "모두 통과"
