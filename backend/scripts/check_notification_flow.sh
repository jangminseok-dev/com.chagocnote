#!/usr/bin/env bash
# 개발 환경에서 알림톡 채널 연동 → 템플릿 승인 → 발신번호 인증·문자 대체 → 예약 접수·리마인드 → 일정 변경 → 실패와 다시 보내기
# → 취소 → 완료와 다음 예약 제안 → 알림장 → 연동 해제까지 게이트웨이를 거쳐 확인한다.
# dev 의 게이트웨이는 가짜(FakeGateway)다 — 토큰·인증번호는 000000, 번호 끝 0000 은 영구 실패(문자 대체가 켜져 있으면 문자로 간다).
# 디스패처는 서버 안에서 돈다 — 줄의 상태는 wait_status 로 몇 초 기다려 본다. 템플릿 승인은 10분 주기라 운영자 스크립트
# (reregister_templates.py --refresh)로 바로 당긴다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_notification_flow.sh
# infra/ 에서 실행해야 한다(운영자 지정과 템플릿 상태 조회를 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문·알림 줄이 남는다.
# 번호·알림장 주소·업체 ID 는 화면에 찍지 않는다 — 단계 이름과 상태만 보인다.
# 요청 본문은 변수·함수로 먼저 만든다 — 맥의 bash 3.2 는 "$( … \" … )" 안의 따옴표 이스케이프를 잘못 가르기도 한다(expect 가 인자 수로 잡는다).
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
SEED="$(printf '%04d' $((STAMP % 10000)))"
PHONE="010${SEED}1234"                                          # 실행마다 다른 번호. 끝이 1234 라 가짜 업체가 성공으로 답한다
PHONE_B="010$(printf '%04d' $(((STAMP + 1) % 10000)))1234"      # 두 번째 보호자
PHONE_BAD="010${SEED}0000"                                      # 끝 0000 — 가짜 업체가 영구 실패로 답한다
PHONE_BAD_B="010$(printf '%04d' $(((STAMP + 1) % 10000)))0000"
ADMIN_PHONE="010$(printf '%08d' $((STAMP % 100000000)))"        # 채널 관리자 번호(업체에만 넘기고 저장하지 않는다)
SENDER="02$(printf '%08d' $((STAMP % 100000000)))"              # 발신번호(유선)
TOKEN_REQ="{\"search_id\":\"nflow-$STAMP\",\"admin_phone\":\"$ADMIN_PHONE\",\"category_code\":\"003001\"}"
LINK_REQ="${TOKEN_REQ%\}},\"token\":\"000000\"}"
WRONG_LINK_REQ="${TOKEN_REQ%\}},\"token\":\"123456\"}"
VERIFY_REQ="{\"phone\":\"$SENDER\"}"
RIGHT_CODE_REQ="{\"phone\":\"$SENDER\",\"code\":\"000000\"}"
WRONG_CODE_REQ="{\"phone\":\"$SENDER\",\"code\":\"111111\"}"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }

field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
expect() {
  if [ $# -ne 3 ]; then echo "실패  $1 (인자 $# 개 — 따옴표가 깨졌다)"; exit 1; fi
  if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi
}
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
pet() { echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}"; }
# family <보호자 이름> <번호> <아이 이름> — 고객과 반려동물을 만들고 "customer_id pet_id" 를 낸다.
family() {
  local body="{\"customer\":{\"name\":\"$1\",\"phone\":\"$2\",\"marketing_consent\":true},\"pet\":$(pet "$3")}"
  call POST "$S/customers" "$staff_token" "$body" | calc "f\"{d['customer']['customer_id']} {d['pets'][0]['pet_id']}\""
}
book() { call POST "$S/visits" "$staff_token" "{\"customer_id\":$1,\"pet_ids\":[$2],\"starts_at\":\"$3\"}" | field "['visits'][0]['visit_id']"; }
act() { call POST "$S/visits/transitions" "$staff_token" "{\"visit_ids\":[$1],\"action\":\"$2\"${3:+,\"cancel_reason\":\"$3\"}}"; }
# notes <방문> — 그 방문의 알림 줄 목록 응답. lines <방문> — 최신순 (종류, 상태) 목록. latest <종류> — 목록 응답에서 그 종류의 가장 최근 줄.
notes() { call GET "$S/visits/$1/notifications" "$staff_token"; }
lines() { notes "$1" | calc "[(i['kind'], i['status']) for i in d['items']]"; }
latest() { python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(next(i for i in d['items'] if i['kind']==sys.argv[1]), ensure_ascii=False))" "$1"; }
line() { notes "$1" | latest "$2"; }
line_id() { line "$1" "$2" | field "['message_id']"; }
# wait_status <message_id> <상태> — 1초 간격으로 최대 15초 기다리고 마지막 상태를 낸다. 디스패처가 서버 안에서 돈다.
wait_status() {
  local s=""; for _ in $(seq 15); do
    s=$(call GET "$S/notifications/$1" "$staff_token" | field "['status']"); [ "$s" = "$2" ] && break; sleep 1
  done; echo "$s"
}
overview() { call GET "$S/notification" "$owner_token"; }
# settings_body <next_visit_enabled> <sms_fallback_enabled> — 설정 전체 교체 본문(아홉 칸 모두).
settings_body() { echo "{\"confirm_enabled\":true,\"reminder_enabled\":true,\"report_enabled\":true,\"change_enabled\":true,\"next_visit_enabled\":$1,\"reminder_time\":\"18:00\",\"next_visit_after_weeks\":null,\"next_visit_cooldown_days\":30,\"sms_fallback_enabled\":$2}"; }
put_settings() { call PUT "$S/notification/settings" "$owner_token" "$(settings_body "$1" "$2")"; }
approve_templates() { docker compose run --rm backend python scripts/reregister_templates.py --refresh --shop "$shop_id" >/dev/null; }
send_report() { call PUT "$S/visits/$1/report" "$staff_token" '{"hidden_media_ids":[]}' >/dev/null; }

# 1. 매장·사장·직원·고객·반려동물
op=$(login "nflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"알림톡흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "nflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "nflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
S="/v1/shops/$shop_id"
read -r customer_id kong < <(family 김민지 "$PHONE" 콩이)
echo "통과  1 매장 $shop_id 에 사장·직원·고객 $customer_id 과 반려동물 $kong 이 있다"
expect "1 연동 전 한눈에 보기는 채널 none, 설정 없음, 템플릿 없음" "$(overview | calc "(d['channel']['status'], d['settings'], d['templates'])")" "('none', None, [])"

# 2. 채널 연동 — 토큰 신청 → 틀린 토큰 → 맞는 토큰
expect "2 직원은 토큰을 신청하지 못한다" "$(status POST "$S/notification/channel/token" "$staff_token" "$TOKEN_REQ")" "403"
expect "2 사장의 토큰 신청은 202" "$(call POST "$S/notification/channel/token" "$owner_token" "$TOKEN_REQ" | field "['status']")" "token_requested"
expect "2 틀린 토큰은 400" "$(call POST "$S/notification/channel" "$owner_token" "$WRONG_LINK_REQ" | field "['code']")" "NOTIFICATION_TOKEN_INVALID"
linked=$(call POST "$S/notification/channel" "$owner_token" "$LINK_REQ")
expect "2 맞는 토큰이면 linked 이고 설정은 기본값" "$(echo "$linked" | calc "(d['channel']['status'], d['settings']['reminder_time'], d['settings']['next_visit_enabled'])")" "('linked', '18:00', False)"
expect "2 기본 5종 템플릿이 심사 중" "$(echo "$linked" | calc "[(t['kind'], t['status']) for t in d['templates']]")" \
  "[('confirm', 'pending'), ('reminder', 'pending'), ('report', 'pending'), ('change', 'pending'), ('cancel', 'pending')]"
expect "2 응답에 업체 ID 가 없다" "$(echo "$linked" | calc "'pf-' in json.dumps(d) or 'tpl-' in json.dumps(d)")" "False"

# 3. 템플릿 승인 — 디스패처의 10분 주기 대신 운영자 스크립트로 당긴다
approve_templates
expect "3 다섯 종류가 승인됐다" "$(overview | calc "[t['status'] for t in d['templates']]")" "['approved', 'approved', 'approved', 'approved', 'approved']"

# 4. 문자 대체 — 발신번호 인증 뒤에만
expect "4 인증 없이 문자 대체를 켜면 409" "$(put_settings false true | field "['code']")" "NOTIFICATION_SENDER_NOT_VERIFIED"
expect "4 발신번호 인증 시작은 202" "$(call POST "$S/notification/sender/verification" "$owner_token" "$VERIFY_REQ" | field "['status']")" "verification_requested"
expect "4 틀린 인증번호는 400" "$(call POST "$S/notification/sender" "$owner_token" "$WRONG_CODE_REQ" | field "['code']")" "NOTIFICATION_TOKEN_INVALID"
verified=$(call POST "$S/notification/sender" "$owner_token" "$RIGHT_CODE_REQ")
expect "4 맞는 인증번호면 발신번호가 인증된다" "$(echo "$verified" | calc "(d['channel']['sender_verified'], d['channel']['sms_fallback_enabled'])")" "(True, False)"
expect "4 직원은 설정을 바꾸지 못한다" "$(status PUT "$S/notification/settings" "$staff_token" "$(settings_body false true)")" "403"
expect "4 인증 뒤에는 문자 대체를 켤 수 있다" "$(put_settings false true | field "['channel']['sms_fallback_enabled']")" "True"

# 5. 예약 접수 — 접수 안내는 바로, 리마인드는 전날 18:00
visit=$(book "$customer_id" "$kong" "$(at 2 14)")
expect "5 예약하면 접수 안내와 리마인드 줄이 생긴다" "$(lines "$visit")" "[('reminder', 'scheduled'), ('confirm', 'scheduled')]"
expect "5 접수 안내가 보내진다" "$(wait_status "$(line_id "$visit" confirm)" sent)" "sent"
expect "5 알림톡으로 갔고 보낸 시각이 있다" "$(line "$visit" confirm | calc "(d['channel_used'], d['sent_at'] is not None, d['share_text'])")" "('alimtalk', True, None)"
expect "5 리마인드는 전날 18:00 예정" "$(line "$visit" reminder | calc "(d['status'], d['scheduled_at'])")" "('scheduled', '$(at 1 18)')"
items=$(notes "$visit")
expect "5 응답에 번호·변수·업체 메시지 ID 가 없다" "$(echo "$items" | calc "any(s in json.dumps(d) for s in ('$PHONE', 'variables', 'fake-', 'starts_at', 'customer_id'))")" "False"

# 6. 일정 변경 — 옛 리마인드는 취소, 새 리마인드와 변경 안내
call POST "$S/visits/reschedule" "$staff_token" "{\"visit_ids\":[$visit],\"starts_at\":\"$(at 3 15)\"}" >/dev/null
expect "6 변경 안내가 보내진다" "$(wait_status "$(line_id "$visit" change)" sent)" "sent"
expect "6 옛 리마인드는 취소되고 새 리마인드가 생긴다" "$(lines "$visit")" "[('change', 'sent'), ('reminder', 'scheduled'), ('reminder', 'canceled'), ('confirm', 'sent')]"
items=$(notes "$visit")
expect "6 취소 이유는 rescheduled, 새 리마인드는 바뀐 전날 18:00" "$(echo "$items" | calc "([i['canceled_reason'] for i in d['items'] if i['kind'] == 'reminder'], d['items'][1]['scheduled_at'])")" "([None, 'rescheduled'], '$(at 2 18)')"

# 7. 실패 — 끝 0000 번호는 영구 실패. 문자 대체가 켜져 있으면 문자로 가고, 끄면 실패 줄에 공유용 문안이 생긴다
read -r bad_customer bad_pet < <(family 이서연 "$PHONE_BAD" 두부)
bad_visit=$(book "$bad_customer" "$bad_pet" "$(at 2 11)")
expect "7 문자 대체가 켜져 있으면 문자로 간다" "$(wait_status "$(line_id "$bad_visit" confirm)" fallback_sent)" "fallback_sent"
expect "7 실제로 나간 길은 sms" "$(line "$bad_visit" confirm | calc "(d['channel_used'], d['share_text'])")" "('sms', None)"
put_settings false false >/dev/null
read -r bad_customer_b bad_pet_b < <(family 최지우 "$PHONE_BAD_B" 보리)
bad_visit_b=$(book "$bad_customer_b" "$bad_pet_b" "$(at 2 12)")
expect "7 문자 대체를 끄면 영구 실패" "$(wait_status "$(line_id "$bad_visit_b" confirm)" failed)" "failed"
failed_line=$(line "$bad_visit_b" confirm)
expect "7 실패 줄에는 공유용 문안이 있고 번호·이름은 없다" "$(echo "$failed_line" | calc "(d['error_kind'], d['share_text'] is not None, '$PHONE_BAD_B' in d['share_text'], '최지우' in d['share_text'])")" "('permanent', True, False, False)"
expect "7 공유용 문안은 매장 이름과 일시가 든 접수 문안이다" "$(echo "$failed_line" | calc "d['share_text'].startswith('[알림톡흐름-$STAMP] ') and '예약이 접수되었어요.' in d['share_text']")" "True"
resent=$(call POST "$S/visits/$bad_visit_b/notifications/confirm/resend" "$staff_token")
resent_id=$(echo "$resent" | calc "d.get('message_id', d.get('code'))")
expect "7 직원이 다시 보내면 201 과 새 줄" "$(echo "$resent" | calc "'message_id' in d")" "True"
expect "7 대기 중에 또 누르면 409" "$(call POST "$S/visits/$bad_visit_b/notifications/confirm/resend" "$staff_token" | field "['code']")" "NOTIFICATION_ALREADY_PENDING"
expect "7 다시 보낸 줄이 맨 앞이고 누른 멤버가 남는다" "$(line "$bad_visit_b" confirm | calc "(d['message_id'] == $resent_id, d['requested_by_member_id'] is not None)")" "(True, True)"
expect "7 다시 보낸 줄도 영구 실패로 끝난다" "$(wait_status "$resent_id" failed)" "failed"

# 8. 취소 — 매장 사정이면 취소 안내, 보호자 요청이면 대기 줄만 취소
shop_cancel=$(book "$customer_id" "$kong" "$(at 4 11)")
expect "8 접수 안내가 먼저 나간다" "$(wait_status "$(line_id "$shop_cancel" confirm)" sent)" "sent"
act "$shop_cancel" cancel shop_reason >/dev/null
expect "8 매장 사정 취소는 취소 안내가 보내진다" "$(wait_status "$(line_id "$shop_cancel" cancel)" sent)" "sent"
expect "8 리마인드는 visit_canceled 로 취소된다" "$(line "$shop_cancel" reminder | calc "(d['status'], d['canceled_reason'])")" "('canceled', 'visit_canceled')"
customer_cancel=$(book "$customer_id" "$kong" "$(at 5 11)")
expect "8 접수 안내가 먼저 나간다" "$(wait_status "$(line_id "$customer_cancel" confirm)" sent)" "sent"
act "$customer_cancel" cancel customer_request >/dev/null
expect "8 보호자 요청 취소는 취소 안내가 없다" "$(lines "$customer_cancel")" "[('reminder', 'canceled'), ('confirm', 'sent')]"

# 9. 완료 — 다음 예약 제안은 켠 뒤부터, 4주 뒤 18:00
done_visit=$(book "$customer_id" "$kong" "$(at 0 13)")
act "$done_visit" start >/dev/null; act "$done_visit" complete >/dev/null
expect "9 다음 예약 제안이 꺼져 있으면 줄이 없다" "$(notes "$done_visit" | calc "[i['kind'] for i in d['items']]")" "['confirm']"
expect "9 다음 예약 제안을 켜면 템플릿이 여섯" "$(put_settings true false | calc "[(t['kind'], t['status']) for t in d['templates']][-1]")" "('next_visit', 'pending')"
approve_templates
expect "9 여섯 종류가 승인됐다" "$(overview | calc "[t['status'] for t in d['templates']]")" "['approved', 'approved', 'approved', 'approved', 'approved', 'approved']"
read -r customer_b pet_b < <(family 박서준 "$PHONE_B" 몽이)
done_visit_b=$(book "$customer_b" "$pet_b" "$(at 0 15)")
act "$done_visit_b" start >/dev/null; act "$done_visit_b" complete >/dev/null
expect "9 완료하면 다음 예약 제안이 4주 뒤 18:00 에 예정된다" "$(line "$done_visit_b" next_visit | calc "(d['status'], d['scheduled_at'])")" "('scheduled', '$(at 28 18)')"

# 10. 알림장 — 보내면 알림장 줄, 같은 링크는 줄이 늘지 않고, 끊고 새로 보내면 새 줄
call PUT "$S/visits/$done_visit/record" "$staff_token" '{"care_note":"눈물 자국 관리","media":[]}' >/dev/null
expect "10 알림장을 보내면 200" "$(status PUT "$S/visits/$done_visit/report" "$staff_token" '{"hidden_media_ids":[]}')" "200"
expect "10 알림장 줄이 보내진다" "$(wait_status "$(line_id "$done_visit" report)" sent)" "sent"
expect "10 응답에 알림장 주소가 없다" "$(notes "$done_visit" | calc "'/r/' in json.dumps(d)")" "False"
send_report "$done_visit"
expect "10 같은 링크를 다시 공유하면 줄이 늘지 않는다" "$(lines "$done_visit")" "[('report', 'sent'), ('confirm', 'sent')]"
expect "10 끊기는 204" "$(status DELETE "$S/visits/$done_visit/report" "$staff_token")" "204"
send_report "$done_visit"
expect "10 새 링크로 보내면 새 알림장 줄" "$(wait_status "$(line_id "$done_visit" report)" sent)" "sent"
expect "10 알림장 줄이 둘" "$(lines "$done_visit")" "[('report', 'sent'), ('report', 'sent'), ('confirm', 'sent')]"

# 11. 연동 해제 — 대기 줄은 전부 취소, 다시 연동할 수 있다
expect "11 해제는 204" "$(status DELETE "$S/notification/channel" "$owner_token")" "204"
reminder_after=$(line "$visit" reminder | calc "(d['status'], d['canceled_reason'])")
next_after=$(line "$done_visit_b" next_visit | calc "(d['status'], d['canceled_reason'])")
expect "11 예정된 리마인드와 다음 예약 제안이 channel_unlinked 로 취소된다" "$reminder_after $next_after" "('canceled', 'channel_unlinked') ('canceled', 'channel_unlinked')"
expect "11 해제 뒤 설정 변경은 409" "$(put_settings false false | field "['code']")" "NOTIFICATION_CHANNEL_NOT_LINKED"
expect "11 다시 토큰을 신청할 수 있다" "$(status POST "$S/notification/channel/token" "$owner_token" "$TOKEN_REQ")" "202"
relinked=$(call POST "$S/notification/channel" "$owner_token" "$LINK_REQ")
expect "11 다시 연동하면 linked 이고 발신번호는 남아 있다" "$(echo "$relinked" | calc "(d['channel']['status'], d['channel']['sender_verified'], len(d['templates']))")" "('linked', True, 5)"

echo "전체 흐름 확인 완료"
