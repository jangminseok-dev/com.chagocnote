#!/usr/bin/env bash
# 개발 환경에서 보호자 회원 흐름을 게이트웨이를 거쳐 확인한다 — 웹 세션 로그인(30분·리프레시 없음) → 알림장 보내기 →
# 받은 링크로 잇기 → 다시 잇기(같은 연결) → 다른 계정은 409 → 내 연결 목록 → 아이들 → 지난 알림장 목록 → 한 장(내부 메모 없음)
# → 매장이 링크를 끊으면 목록에서 사라짐 → 다시 보내면 다시 보임 → 매장이 보는 연결 → 매장이 끊으면 보호자 읽기 404
# → 다시 잇기 → 보호자가 끊기 → 닫힌 토큰으로 잇기 410 → (⑫) 알림장 끝의 리뷰 줄·알림장마다 빼기 → 모아 보기·몸무게
# → 가족 초대·잇기·목록·한 명 끊기 → 매장의 끊기가 가족까지.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_guardian_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문·알림장·연결이 남는다.
# 알림장 토큰은 헤더(X-Report-Token)로, 가족 초대 코드는 헤더(X-Family-Invite)로만 넘기고 화면에 찍지 않는다 — 단계 이름과 상태 코드·판정만 보인다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
MARK="내부표식$STAMP"                                 # 내부 메모에 넣는 표식. 보호자 응답 어디에도 없어야 한다
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
has() { python3 -c "import json,sys; print(sys.argv[1] in json.dumps(json.load(sys.stdin), ensure_ascii=False))" "$1"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
# web_login <이름> — 보호자 웹 세션. 본문은 변수로 만든다(맥의 bash 3.2 는 명령 치환 안의 {…,…} 를 쪼갠다).
web_login() { local body="{\"provider\":\"dev\",\"token\":\"$1\",\"session\":\"web\"}"; curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "$body"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# claim <보호자 토큰> <알림장 토큰> — 잇기. 응답 본문. claim_status 는 상태 코드.
claim() { curl -s -X POST "$BASE/v1/me/guardian/links" -H "Authorization: Bearer $1" ${2:+-H "X-Report-Token: $2"}; }
claim_status() { curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/me/guardian/links" -H "Authorization: Bearer $1" ${2:+-H "X-Report-Token: $2"}; }
token_of() { local url; url=$(field "['link']['url']"); echo "${url##*/}"; }
SEND='{"hidden_media_ids":[]}'

# 1. 매장·고객·완료한 방문·알림장
op=$(login "gflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop_req="{\"name\":\"보호자흐름-$STAMP\"}"
shop=$(call POST /v1/platform/shops "$op_token" "$shop_req")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "gflow-owner-$STAMP" | field "['access_token']")
accept_req="{\"code\":\"$owner_code\"}"
call POST /v1/invites/accept "$owner_token" "$accept_req" >/dev/null
S="/v1/shops/$shop_id"
bath=$(call GET "$S/menus" "$owner_token" | field "['items'][0]['menu_id']")
family_req="{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\"pet\":{\"name\":\"콩이\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}}"
registered=$(call POST "$S/customers" "$owner_token" "$family_req")
customer_id=$(echo "$registered" | field "['customer']['customer_id']"); pet_id=$(echo "$registered" | field "['pets'][0]['pet_id']")
visit_req="{\"customer_id\":$customer_id,\"pet_ids\":[$pet_id],\"starts_at\":\"$(at -1 11)\",\"menu_ids\":[$bath]}"
visit_id=$(call POST "$S/visits" "$owner_token" "$visit_req" | field "['visits'][0]['visit_id']")
V="$S/visits/$visit_id"
start_req="{\"visit_ids\":[$visit_id],\"action\":\"start\"}"
call POST "$S/visits/transitions" "$owner_token" "$start_req" >/dev/null
record_req="{\"weight_kg\":3.4,\"care_note\":\"눈물 자국을 닦았어요.\",\"internal_note\":\"$MARK\",\"payment_method\":\"card\",\"total_amount\":30000,\"items\":[{\"menu_id\":$bath,\"amount\":30000}],\"media\":[]}"
call PUT "$V/record" "$owner_token" "$record_req" >/dev/null
complete_req="{\"visit_ids\":[$visit_id],\"action\":\"complete\"}"
call POST "$S/visits/transitions" "$owner_token" "$complete_req" >/dev/null
report_token=$(call PUT "$V/report" "$owner_token" "$SEND" | token_of)
expect "1 완료한 방문에 알림장을 보냈다(토큰 43글자)" "${#report_token}" "43"

# 2. 보호자 웹 세션 — 30분, 리프레시 없음
web=$(web_login "gflow-guardian-$STAMP"); g_token=$(echo "$web" | field "['access_token']")
expect "2 웹 세션은 리프레시 토큰이 없다" "$(echo "$web" | field "['refresh_token']")" "None"
expect "2 웹 세션의 수명은 30분이다" "$(echo "$web" | field "['expires_in']")" "1800"
expect "2 웹 세션 토큰으로 내 정보를 읽는다" "$(status GET /v1/me "$g_token")" "200"

# 3. 잇기
expect "3 토큰 없이 잇기는 404" "$(claim_status "$g_token" "")" "404"
linked=$(claim "$g_token" "$report_token"); link_id=$(echo "$linked" | field "['link_id']")
expect "3 받은 링크로 이으면 연결이 생긴다" "$([ "$link_id" -gt 0 ] && echo 예)" "예"
expect "3 다시 이으면 200 이고 같은 연결이다" "$(claim "$g_token" "$report_token" | field "['link_id']")" "$link_id"
other_token=$(web_login "gflow-other-$STAMP" | field "['access_token']")
expect "3 다른 계정이 같은 링크로 이으면 409" "$(claim "$other_token" "$report_token" | field "['code']")" "GUARDIAN_ALREADY_LINKED"

# 4. 내 연결과 지난 알림장
L="/v1/me/guardian/links"
links=$(call GET "$L" "$g_token")
expect "4 내 연결 목록에 매장 이름이 있다" "$(echo "$links" | field "['items'][0]['shop_name']")" "보호자흐름-$STAMP"
expect "4 다른 계정의 목록은 비어 있다" "$(call GET "$L" "$other_token" | field "['items'].__len__()")" "0"
expect "4 아이들에 콩이가 있다" "$(call GET "$L/$link_id/pets" "$g_token" | field "['items'][0]['name']")" "콩이"
page=$(call GET "$L/$link_id/reports" "$g_token")
expect "4 지난 알림장이 한 장이다" "$(echo "$page" | field "['items'].__len__()")" "1"
report_id=$(echo "$page" | field "['items'][0]['report_id']")
one=$(call GET "$L/$link_id/reports/$report_id" "$g_token")
expect "4 한 장에 케어 메모가 있다" "$(echo "$one" | field "['care_note']")" "눈물 자국을 닦았어요."
expect "4 한 장에 내부 메모가 없다" "$(echo "$one" | has "$MARK")" "False"
expect "4 로그인한 보호자에게는 기간이 없다" "$(echo "$one" | field "['expires_at']")" "None"
expect "4 남의 연결로는 읽지 못한다" "$(call GET "$L/$link_id/reports" "$other_token" | field "['code']")" "GUARDIAN_LINK_NOT_FOUND"

# 5. 매장이 링크를 끊으면 사라지고 다시 보내면 다시 보인다
expect "5 매장이 링크를 끊는다" "$(status DELETE "$V/report" "$owner_token")" "204"
expect "5 끊은 알림장은 목록에 없다" "$(call GET "$L/$link_id/reports" "$g_token" | field "['items'].__len__()")" "0"
expect "5 끊은 알림장의 한 장은 404" "$(status GET "$L/$link_id/reports/$report_id" "$g_token")" "404"
expect "5 닫힌 토큰으로 잇기는 410" "$(claim "$other_token" "$report_token" | field "['code']")" "REPORT_CLOSED"
new_token=$(call PUT "$V/report" "$owner_token" "$SEND" | token_of)
expect "5 다시 보내면 다시 한 장이 보인다" "$(call GET "$L/$link_id/reports" "$g_token" | field "['items'].__len__()")" "1"

# 6. 매장이 보고 끊는다
GL="$S/customers/$customer_id/guardian-link"
seen=$(call GET "$GL" "$owner_token")
expect "6 매장은 연결됨을 본다" "$(echo "$seen" | field "['linked']")" "True"
expect "6 매장 응답은 여부와 날짜와 가족 수뿐이다" "$(echo "$seen" | python3 -c "import json,sys; print(sorted(json.load(sys.stdin)))")" "['family_count', 'linked', 'linked_at']"
expect "6 매장이 연결을 끊는다" "$(status DELETE "$GL" "$owner_token")" "204"
expect "6 끊긴 보호자의 읽기는 404" "$(call GET "$L/$link_id/reports" "$g_token" | field "['code']")" "GUARDIAN_LINK_NOT_FOUND"
expect "6 끊긴 보호자의 목록은 비어 있다" "$(call GET "$L" "$g_token" | field "['items'].__len__()")" "0"
expect "6 매장은 연결 없음을 본다" "$(call GET "$GL" "$owner_token" | field "['linked']")" "False"

# 7. 다시 잇고 보호자가 끊는다
again=$(claim "$g_token" "$new_token" | field "['link_id']")
expect "7 새 링크로 다시 이으면 새 연결이다" "$([ "$again" != "$link_id" ] && echo 예)" "예"
expect "7 보호자가 끊는다" "$(status DELETE "$L/$again" "$g_token")" "204"
expect "7 끊은 뒤 다시 끊으면 404" "$(status DELETE "$L/$again" "$g_token")" "404"

# 8. 알림장 끝의 리뷰 줄(⑫) — 주소를 넣으면 나오고 알림장마다 뺄 수 있다
public() { curl -s "$BASE/v1/public/report" -H "X-Report-Token: $1"; }
settings_req='{"link_days":30,"show_menus":true,"show_shop_info":true,"show_weight":true,"show_amount":false,"review_url":"https://m.place.naver.com/place/1/review"}'
expect "8 리뷰 주소 넣기 200" "$(status PUT "$S/report-settings" "$owner_token" "$settings_req")" "200"
expect "8 알림장 끝에 기본 문구로 나온다" "$(public "$new_token" | field "['review_text']")" "미용이 마음에 드셨다면 후기를 남겨 주세요"
call PUT "$V/report" "$owner_token" '{"hidden_media_ids":[],"show_review":false}' >/dev/null
expect "8 이 알림장만 빼면 칸이 없다" "$(public "$new_token" | python3 -c "import json,sys; print('review_url' in json.load(sys.stdin))")" "False"
call PUT "$V/report" "$owner_token" "$SEND" >/dev/null

# 9. 모아 보기와 몸무게(⑫) — 다시 이은 연결로
primary=$(claim "$g_token" "$new_token" | field "['link_id']")
media=$(call GET "$L/$primary/media" "$g_token")
expect "9 모아 보기의 칸" "$(echo "$media" | python3 -c "import json,sys; print(sorted(json.load(sys.stdin)))")" "['items', 'next_cursor', 'years']"
expect "9 몸무게를 켠 매장은 몸무게가 보인다" "$(call GET "$L/$primary/pets/$pet_id/weights" "$g_token" | field "['items'][0]['weight_kg']")" "3.4"
expect "9 받은 적 없는 아이는 404" "$(status GET "$L/$primary/pets/999999/weights" "$g_token")" "404"

# 10. 가족과 함께 보기(⑫) — 초대 → 다른 계정이 잇기 → 같은 기록 → 한 명 끊기 → 매장의 끊기가 가족까지
invite() { call POST "$L/$primary/family-invites" "$g_token" | field "['code']"; }
join() { curl -s -X POST "$BASE/v1/me/guardian/family-links" -H "Authorization: Bearer $1" -H "X-Family-Invite: $2"; }
fam_token=$(web_login "gflow-family-$STAMP" | field "['access_token']")
code=$(invite)
expect "10 초대 코드는 43글자다" "${#code}" "43"
family=$(join "$fam_token" "$code" | field "['link_id']")
expect "10 가족이 같은 알림장을 본다" "$(call GET "$L/$family/reports" "$fam_token" | field "['items'].__len__()")" "1"
expect "10 쓴 초대는 다시 쓰지 못한다" "$(join "$other_token" "$code" | field "['code']")" "GUARDIAN_INVITE_NOT_FOUND"
expect "10 기본 보호자는 가족 한 줄을 본다" "$(call GET "$L/$primary/family" "$g_token" | field "['items'][0]['unseen']")" "True"
expect "10 매장은 가족의 수만 본다" "$(call GET "$GL" "$owner_token" | field "['family_count']")" "1"
expect "10 가족은 초대하지 못한다" "$(status POST "$L/$family/family-invites" "$fam_token")" "404"
expect "10 기본 보호자가 그 한 명을 끊는다" "$(status DELETE "$L/$primary/family/$family" "$g_token")" "204"
expect "10 끊긴 가족의 읽기는 404" "$(status GET "$L/$family/reports" "$fam_token")" "404"
family=$(join "$fam_token" "$(invite)" | field "['link_id']")
expect "10 매장이 끊으면" "$(status DELETE "$GL" "$owner_token")" "204"
expect "10 가족도 함께 끊긴다" "$(status GET "$L/$family/reports" "$fam_token")" "404"
echo "전체 흐름 확인 완료"
