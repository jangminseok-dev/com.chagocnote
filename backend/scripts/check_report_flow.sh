#!/usr/bin/env bash
# 개발 환경에서 알림장 설정 → 미리보기 → 사진 하나 빼고 보내기 → 공개 조회 → 열람 신호 → 되돌리기 거절 → 끊기 → 다시 보내기
# → 위조 토큰 → 내려받기까지 게이트웨이와 MinIO 를 거쳐 확인한다. 공개 조회는 로그인 없이 헤더 X-Report-Token 으로 간다.
# 사용: cd infra && docker compose up -d && docker compose run --rm backend python scripts/ensure_media_bucket.py \
#       && bash ../backend/scripts/check_report_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 와 버킷에 확인용 매장·유저·고객·방문·사진·알림장 링크가 남는다.
# 토큰과 서명 URL 은 화면에 찍지 않는다 — 비교는 같다/다르다로 바꿔서 하고, 단계 이름과 상태 코드만 보인다.
# 공개 요청은 열 번 남짓, 그 가운데 404 는 둘이다(횟수 제한: 분당 60회, 404 는 10분에 20회).
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
MARK="내부표식$STAMP"                                 # 내부 메모에 넣는 표식. 공개 응답 어디에도 없어야 한다
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
# has <글자열> — JSON 응답 전체(키·값)에 그 글자열이 있는지. 한글이 \u 로 와도 풀어서 본다.
has() { python3 -c "import json,sys; print(sys.argv[1] in json.dumps(json.load(sys.stdin), ensure_ascii=False))" "$1"; }
same() { if [ "$1" = "$2" ]; then echo 같다; else echo 다르다; fi; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# open_report <토큰> — 공개 조회. 로그인이 없다. 토큰이 비면 헤더도 보내지 않는다.
open_report() { curl -s "$BASE/v1/public/report" ${1:+-H "X-Report-Token: $1"}; }
open_status() { curl -s -o /dev/null -w '%{http_code}' "$BASE/v1/public/report" ${1:+-H "X-Report-Token: $1"}; }
viewed_status() { curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/public/report/viewed" ${1:+-H "X-Report-Token: $1"}; }
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
# send <뺄 미디어 ID 목록> — 알림장을 보내고(또는 다시 공유하고) 응답을 낸다.
send() { call PUT "$V/report" "$staff_token" "{\"hidden_media_ids\":[$1]}"; }
token_of() { local url; url=$(field "['link']['url']"); echo "${url##*/}"; }

# 1. 매장·고객·방문
op=$(login "rflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"알림장흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "rflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "rflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
echo "통과  1 매장 $shop_id 에 사장과 직원이 있다"

registered=$(call POST "$S/customers" "$staff_token" "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\
\"pet\":{\"name\":\"콩이\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\
\"weight_kg\":3.2,\"no_known_conditions\":true}}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
# 어제 11시 예약을 시작한다 — 실행 시각과 상관없이 자정을 넘기지 않는다.
visit=$(call POST "$S/visits" "$staff_token" "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at -1 11)\"}" \
  | field "['visits'][0]['visit_id']")
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"start\"}" >/dev/null
V="$S/visits/$visit"

# 2. 사진 둘과 기록
before=$(photo "$staff_token"); after=$(photo "$staff_token")
bath=$(call GET "$S/menus" "$staff_token" | field "['items'][0]['menu_id']")
saved=$(call PUT "$V/record" "$staff_token" "{\"weight_kg\":3.4,\"care_note\":\"눈물 자국 관리\",\"internal_note\":\"$MARK\",\
\"payment_method\":\"card\",\"total_amount\":25000,\"items\":[{\"menu_id\":$bath,\"amount\":28000}],\
\"media\":[{\"media_id\":$before,\"phase\":\"before\",\"sort_order\":0},{\"media_id\":$after,\"phase\":\"after\",\"sort_order\":0}]}")
expect "2 사진 둘과 두 메모를 기록에 적었다" "$(echo "$saved" | calc "(len(d['media']), d['internal_note'] == '$MARK')")" "(2, True)"
expect "2 완료 전에는 보내지 못한다" "$(send "" | field "['code']")" "VISIT_NOT_COMPLETED"
call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"complete\"}" >/dev/null

# 3. 알림장 설정
expect "3 설정의 처음 값은 30일, 메뉴·매장 정보만 켬" "$(call GET "$S/report-settings" "$staff_token" \
  | calc "(d['link_days'], d['show_menus'], d['show_shop_info'], d['show_weight'], d['show_amount'])")" "(30, True, True, False, False)"
ALL_ON='{"link_days":30,"show_menus":true,"show_shop_info":true,"show_weight":true,"show_amount":true}'
expect "3 직원은 설정을 바꾸지 못한다" "$(status PUT "$S/report-settings" "$staff_token" "$ALL_ON")" "403"
expect "3 사장이 금액과 몸무게를 켠다" "$(call PUT "$S/report-settings" "$owner_token" "$ALL_ON" \
  | calc "(d['show_weight'], d['show_amount'])")" "(True, True)"

# 4. 미리보기 → 사진 하나를 빼고 보내기
expect "4 미리보기는 사진 둘을 주고 링크는 아직 없다" "$(call GET "$V/report" "$staff_token" \
  | calc "(len(d['report']['media']), d['link']['status'], d['link']['url'] is None)")" "(2, 'none', True)"
sent=$(send "$before")
expect "4 전 사진을 빼고 보냈다" "$(echo "$sent" | calc "(d['link']['status'], sorted(m['media_id'] for m in d['report']['media'] if m['hidden']) == [$before])")" "('live', True)"
token=$(echo "$sent" | token_of)
expect "4 링크의 끝이 토큰 43글자다" "${#token}" "43"

# 5. 공개 조회
opened=$(open_report "$token")
expect "5 뺀 사진은 없고 후 사진 하나만 있다" "$(echo "$opened" | calc "[m['phase'] for m in d['media']]")" "['after']"
expect "5 내부 메모 표식이 없다" "$(echo "$opened" | has "$MARK")" "False"
expect "5 보호자 이름과 전화번호가 없다" "$(echo "$opened" | calc "('김민지' in json.dumps(d, ensure_ascii=False), '$PHONE' in json.dumps(d))")" "(False, False)"
expect "5 반려동물 이름과 케어 메모가 있다" "$(echo "$opened" | calc "(d['pet_name'], d['care_note'])")" "('콩이', '눈물 자국 관리')"
expect "5 금액과 몸무게 칸이 있다" "$(echo "$opened" | calc "(d['total_amount'], d['menus'][0]['amount'], d['weight_kg'])")" "(25000, 28000, 3.4)"
expect "5 검색과 캐시를 막는 헤더가 있다" "$(curl -s -o /dev/null -D - "$BASE/v1/public/report" -H "X-Report-Token: $token" \
  | tr -d '\r' | grep -ci -e '^cache-control: private, no-store$' -e '^x-robots-tag: noindex, nofollow$')" "2"

# 6. 금액을 끄면 칸이 없다
call PUT "$S/report-settings" "$owner_token" \
  '{"link_days":30,"show_menus":true,"show_shop_info":true,"show_weight":true,"show_amount":false}' >/dev/null
expect "6 금액을 끄면 금액 칸이 없고 몸무게는 남는다" "$(open_report "$token" \
  | calc "('total_amount' in d, 'amount' in d['menus'][0], 'weight_kg' in d)")" "(False, False, True)"

# 7. 열람 신호
expect "7 조회만으로는 열람이 남지 않는다" "$(call GET "$V" "$staff_token" | calc "d['report']['first_viewed_at']")" "None"
expect "7 열람 신호는 204" "$(viewed_status "$token")" "204"
expect "7 방문 상세에 처음 연 시각이 있다" "$(call GET "$V" "$staff_token" \
  | calc "(d['report']['status'], d['report']['first_viewed_at'] is not None)")" "('live', True)"
expect "7 하루 목록과 피드에 보냄 표시" "$(echo "$(call GET "$S/visits?date=$(at -1 11 | cut -c1-10)" "$staff_token" \
  | calc "[v['report_sent'] for v in d['items'] if v['visit']['visit_id'] == $visit]") $(call GET "$S/visits/feed?pet_id=$kong" "$staff_token" \
  | calc "d['items'][0]['report_sent']")")" "[True] True"

# 8. 보낸 방문은 되돌리거나 기록을 지울 수 없다
expect "8 되돌리기는 409" "$(call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$visit],\"action\":\"revert\"}" | field "['code']")" "VISIT_REPORT_SENT"
expect "8 기록 삭제도 409" "$(call DELETE "$V/record" "$owner_token" | field "['code']")" "VISIT_REPORT_SENT"

# 9. 다시 보내기 — 같은 링크
expect "9 다시 보내면 같은 링크다" "$(same "$(send "$before" | token_of)" "$token")" "같다"

# 10. 끊기
expect "10 끊기는 204" "$(status DELETE "$V/report" "$staff_token")" "204"
expect "10 끊은 링크의 공개 조회는 410" "$(open_report "$token" | field "['code']")" "REPORT_CLOSED"
expect "10 끊은 링크의 열람 신호도 410" "$(viewed_status "$token")" "410"
expect "10 방문은 안 보냄으로 돌아간다" "$(call GET "$V" "$staff_token" | calc "d['report']['status']")" "none"
expect "10 끊을 링크가 없으면 404" "$(call DELETE "$V/report" "$staff_token" | field "['code']")" "REPORT_NOT_FOUND"

# 11. 다시 보내기 — 새 링크
resent=$(send "$before")
new_token=$(echo "$resent" | token_of)
expect "11 끊은 뒤 보내면 다른 링크다" "$(same "$new_token" "$token")" "다르다"
expect "11 옛 토큰은 여전히 410, 새 토큰은 200" "$(open_status "$token") $(open_status "$new_token")" "410 200"
expect "11 새 링크는 아직 열지 않았고 뺀 사진은 빠져 있다" "$(echo "$resent" \
  | calc "(d['link']['first_viewed_at'], [m['media_id'] for m in d['report']['media'] if m['hidden']] == [$before])")" "(None, True)"

# 12. 우리가 만들지 않은 토큰
if [ "${new_token:0:1}" = A ]; then forged="B${new_token:1}"; else forged="A${new_token:1}"; fi
expect "12 위조한 토큰은 404" "$(open_report "$forged" | field "['code']")" "REPORT_NOT_FOUND"
expect "12 헤더가 없으면 404" "$(open_status "")" "404"

# 13. 내려받기
download=$(open_report "$new_token" | field "['media'][0]['download_url']")
expect "13 내려받기 주소는 첨부 파일로 내려온다" "$(curl -s -o /dev/null -D - "$download" | tr -d '\r' \
  | grep -ci '^content-disposition: attachment; filename="chagocnote-[0-9]*\.jpg"$')" "1"

echo "전체 흐름 확인 완료"
