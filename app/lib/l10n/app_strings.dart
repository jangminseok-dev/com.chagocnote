/// 앱 전체에서 쓰는 사용자 노출 문자열. 전부 한국어다.
///
/// 화면은 이 파일의 상수만 쓰고, 문자열을 직접 쓰지 않는다. 오류 문구는
/// `messageFor`(`core/error/error_messages.dart`)를 대신 쓴다.
class AppStrings {
  const AppStrings._();

  static const appName = '차곡노트';
  static const retry = '다시 시도';
  static const back = '뒤로';
  static const goBack = '돌아가기';

  // 로그인
  static const continueWithKakao = '카카오로 계속하기';
  static const continueWithGoogle = 'Google로 계속하기';
  static const continueWithApple = 'Apple로 계속하기';
  static const devNameLabel = '이름';
  static const devSignIn = '개발용 로그인';
  static const devNameRequired = '이름을 입력해 주세요.';
  static const sessionExpiredBanner = '보안을 위해 다시 로그인해 주세요.';

  // 초대 코드
  static const inviteCodeLabel = '초대 코드';
  static const inviteCodeRequired = '초대 코드를 입력해 주세요.';
  static const inviteSubmit = '참여하기';
  static const accountSettings = '계정 설정';
  static const logout = '로그아웃';

  // 매장 선택
  static const selectShopTitle = '매장 선택';
  static const roleOwner = '사장';
  static const roleStaff = '직원';

  // 홈 셸
  static const settingsLabel = '설정';
  static const tabCalendar = '캘린더';
  static const tabCustomers = '고객';
  static const tabSales = '매출';

  // 설정 허브
  static const settingsSectionShop = '매장';
  static const settingsSectionOtherShops = '다른 매장';
  static const settingsSectionAccount = '계정';
  static const settingsMembers = '멤버';
  static const settingsShopInfo = '매장 정보';
  static const settingsSwitchShop = '매장 바꾸기';
  static const settingsJoinByInvite = '초대 코드로 합류';
  static const settingsAccount = '계정';

  // 멤버
  static const createInvite = '초대 코드 만들기';
  static const inviteExpiresAtLabel = '만료';
  static const copy = '복사';
  static const promoteToOwner = '사장으로 변경';
  static const demoteToStaff = '직원으로 변경';
  static const removeMember = '내보내기';
  static const removeMemberConfirmTitle = '정말 내보낼까요?';
  static const cancel = '취소';

  // 매장 정보
  static const shopName = '매장 이름';
  static const shopPhone = '전화번호';
  static const shopAddress = '주소';
  static const save = '저장';
  static const saved = '저장했어요';
  static const shopNameRequired = '매장 이름을 입력해 주세요.';

  // 계정
  static const providerKakao = '카카오';
  static const providerGoogle = 'Google';
  static const providerApple = 'Apple';
  static const providerDev = '개발용';
  static const accountLinkedMethods = '로그인 수단';
  static const accountAddMethod = '로그인 수단 추가';
  static const unlink = '해제';
  static const unlinkOnlyOneCaption = '마지막 로그인 수단은 해제할 수 없어요.';
  static const unlinkConfirmMessage = '해제하면 다른 모든 기기에서 로그아웃돼요.';
  static const withdraw = '회원 탈퇴';

  // 재인증
  static const reauthPromptTitle = '보안을 위해 다시 로그인해 주세요';
  static const reauthMismatch = '다른 계정이에요. 이 계정에 연결된 로그인 수단으로 다시 로그인해 주세요.';

  // 회원 탈퇴
  static const withdrawNoticeIrreversible = '되돌릴 수 없어요.';
  static const withdrawNoticeShopRecordsStay = '매장의 기록은 매장에 남아요.';
  static const withdrawNoticeMembershipGone = '소속과 초대 코드는 사라져요.';
  static const withdrawNoticeNewAccount = '같은 소셜 계정으로 다시 가입하면 새 계정이 돼요.';
  static const withdrawConfirmCheckbox = '안내를 확인했어요';
  static const withdrawSubmit = '탈퇴하기';
  static const withdrawShopCloseTitle = '혼자 운영하는 매장도 함께 닫혀요';
  static const withdrawShopCloseConfirm = '매장을 닫고 탈퇴';
  static const goToMembers = '멤버 관리로 이동';

  // 고객·반려동물
  static const speciesDog = '강아지';
  static const speciesCat = '고양이';
  static const sexFemale = '여아';
  static const sexMale = '남아';
  static const neutered = '중성화';

  static const edit = '수정';
  static const delete = '삭제';
  static const more = '더 보기';
  static const none = '없음';
  static const petTabBasic = '기본';
  static const petTabConditions = '질병';
  static const petTabOwner = '보호자';
  static const petTabRecords = '기록';
  static const petRecordsEmpty = '아직 끝난 미용 기록이 없어요';
  static const loadMore = '더 보기';
  static const passedAwayBadge = '무지개다리';
  static const markPassedAway = '무지개다리 표시';
  static const unmarkPassedAway = '무지개다리 되돌리기';
  static const markPassedAwayConfirm = '무지개다리를 건넜다고 표시할까요? 목록에서 숨겨지고 기록은 남아요.';
  static const deletePet = '반려동물 삭제';
  static const deletePetConfirm =
      '잘못 등록한 반려동물을 삭제할까요? 질병 기록도 함께 지워지고 되돌릴 수 없어요.';
  static const birthDateLabel = '생일';
  static const birthYearLabel = '태어난 해';
  static const ageUnknown = '모름';
  static const weightLabel = '몸무게';
  static const petMemoLabel = '특이사항';
  static const noKnownConditions = '질병 없음';
  static const noKnownConditionsConfirmed = '질병 없음 — 확인함';
  static const siblingsLabel = '같은 보호자의 아이';
  static const ownerNameLabel = '이름';
  static const ownerPhoneLabel = '전화번호';
  static const ownerPhoneAltLabel = '보조 연락처';
  static const marketingConsentLabel = '마케팅 수신';
  static const marketingAgreed = '동의';
  static const marketingDeclined = '거부';
  static const customerMemoLabel = '메모';
  static const editOwner = '보호자 수정';
  static const addPet = '반려동물 추가';

  static String conditionCount(int count) => '질병 $count';
  static String birthYearText(int year) => '$year년생';

  static const customersTitle = '고객';
  static const viewAsList = '목록으로 보기';
  static const viewAsGrid = '격자로 보기';
  static const sortRecent = '최근순';
  static const sortName = '가나다순';
  static const sortLastVisit = '최근 방문순';
  static const upcomingVisitsLabel = '다가오는 예약';
  static const noUpcomingVisits = '없음';
  static const includePassed = '무지개다리 포함';
  static const customerSearchHint = '번호 뒷자리, 이름, 반려동물 (초성 가능)';
  static const customersEmpty = '등록된 고객이 없어요';
  static const customersEmptyCaption = '+ 버튼으로 첫 고객을 등록해 보세요.';
  static const customersNoMatch = '찾는 고객이 없어요';
  static const conditionsBadge = '질병';

  static String petCountText(int count) => '$count마리';

  static const petNameLabel = '이름';
  static const speciesLabelText = '종류';
  static const breedLabel = '품종';
  static const sexLabelText = '성별';
  static const neuteredYes = '중성화 했어요';
  static const neuteredNo = '안 했어요';
  static const ageLabel = '나이';
  static const ageByBirthDate = '생일';
  static const ageByBirthYear = '태어난 해';
  static const birthDateHint = 'YYYY.MM.DD';
  static const birthYearHint = '예: 2021';
  static const weightHint = '예: 3.2';
  static const weightUnit = 'kg';
  static const conditionsLabel = '질병';
  static const conditionOther = '기타';
  static const conditionOtherHint = '질병 이름';
  static const conditionNoteHint = '메모 (선택)';
  static const removeCondition = '이 질병 빼기';
  static const petMemoHint = '특이사항 (선택)';
  static const petNameRequired = '이름을 입력해 주세요.';
  static const speciesRequired = '종류를 골라 주세요.';
  static const breedRequired = '품종을 입력해 주세요.';
  static const sexRequired = '성별을 골라 주세요.';
  static const neuteredRequired = '중성화 여부를 골라 주세요.';
  static const ageRequired = '생일·태어난 해·모름 중 하나를 골라 주세요.';
  static const birthDateInvalid = '생일을 YYYY.MM.DD 로 입력해 주세요(오늘까지, 40년 전부터).';
  static const birthYearInvalid = '태어난 해를 확인해 주세요(올해까지, 40년 전부터).';
  static const weightInvalid = '몸무게를 kg 으로 입력해 주세요(예: 3.2).';
  static const healthRequired = '질병을 고르거나 "질병 없음"을 눌러 주세요.';
  static const otherLabelRequired = '기타 질병의 이름을 입력해 주세요.';
  static const addPetTitle = '반려동물 추가';
  static const editPetTitle = '반려동물 수정';

  /// 품종 입력 칸 아래에 보이는 추천(누르면 채운다).
  static const dogBreeds = [
    '말티즈',
    '푸들',
    '포메라니안',
    '비숑',
    '시츄',
    '요크셔테리어',
    '치와와',
    '믹스',
  ];
  static const catBreeds = [
    '코리안 숏헤어',
    '러시안 블루',
    '페르시안',
    '브리티시 숏헤어',
    '스코티시 폴드',
    '믹스',
  ];

  static const ownerNameHint = '예: 김민지, 콩이 보호자';
  static const phoneHint = '예: 010-1234-5678';
  static const phoneAltHint = '보조 연락처 (선택)';
  static const customerMemoHint = '메모 (선택)';
  static const ownerNameRequired = '이름을 입력해 주세요.';
  static const phoneInvalid = '전화번호를 확인해 주세요.';
  static const phoneAltInvalid = '보조 연락처를 확인해 주세요.';
  static const consentRequired = '마케팅 수신 동의 여부를 골라 주세요.';
  static const editOwnerTitle = '보호자 수정';
  static const deleteCustomer = '고객 삭제';
  static const deleteCustomerConfirm =
      '고객을 삭제할까요? 보호자의 이름·전화번호·메모와 반려동물의 이름·질병 기록이 지워지고 되돌릴 수 없어요.';

  static const registerCustomer = '고객 등록';
  static const registerStepPhone = '전화번호';
  static const registerStepOwner = '보호자';
  static const registerStepPet = '반려동물';
  static const next = '다음';
  static const addPetToExisting = '이 보호자에게 반려동물 추가';

  static String registerStepTitle(String step, int index) => '$step $index / 3';
  static String lookupFound(String name, List<String> petNames) =>
      petNames.isEmpty
      ? '이미 등록된 번호예요 — $name'
      : '이미 등록된 번호예요 — $name (${petNames.join(', ')})';

  // 예약·방문
  static const weekdaysShort = ['월', '화', '수', '목', '금', '토', '일'];
  static const statusReserved = '예약됨';
  static const statusUnknown = '알 수 없음';
  static const statusInProgress = '미용 중';
  static const statusCompleted = '완료';
  static const statusCanceled = '취소';
  static const statusNoShow = '노쇼';
  static const ownerOnly = '보호자만';
  static const deletedCustomer = '삭제된 고객';
  static const noMenu = '메뉴 없음';
  static const reserveWhoTitle = '누구의 예약인가요';
  static const reserveWhenTitle = '언제 오나요';
  static const reserveNoCustomer = '찾는 고객이 없나요?';
  static const registerNewCustomer = '새 고객 등록';
  static const changeCustomer = '바꾸기';
  static const visitDateLabel = '날짜';
  static const visitTimeLabel = '시작';
  static const menuDurationLabel = '메뉴 · 소요 (선택)';
  static const menuLabel = '메뉴';
  static const durationLabel = '소요';
  static const shorter = '소요 줄이기';
  static const longer = '소요 늘리기';
  static const visitMemoHint = '메모 (선택)';
  static const prefilledFromLast = '지난번과 같게 채웠어요. 그대로 저장해도 돼요.';
  static const pickPetFirst = '반려동물이나 "보호자만"을 골라 주세요';
  static const pickTimeFirst = '시작 시각을 골라 주세요';
  static const startNow = '지금 시작';
  static const prevWeek = '이전 주';
  static const nextWeek = '다음 주';
  static const pickMinuteTitle = '10분 단위로 고르기';
  static const pickMinuteHint = '시간 칸을 길게 누르면 10분 단위로 고를 수 있어요.';
  static const warningOverlap = '이미 예약이 있는 시간이에요';
  static const warningClosedDay = '쉬는 날이에요';
  static const warningOutsideHours = '영업시간 밖이에요';

  // 카톡 예약 초안(③-A3)
  static const pasteFromKakao = '카톡 붙여넣기';
  static const clipboardEmpty = '복사한 글이 없어요';
  static const draftTitle = '카톡 예약 초안';
  static const draftReceivedText = '받은 글';
  static const draftOwnerSection = '보호자';
  static const draftNoCandidates = '찾은 보호자가 없어요';
  static const draftGuessed = '짐작';
  static const draftEmptyValue = '—';
  static const draftContinue = '예약 이어서';
  static const draftFindCustomer = '고객 찾기';
  static const draftHint = '확인한 뒤 저장돼요. 짐작한 칸은 다음 화면에서 고칠 수 있어요.';

  static const duplicateVisitNotice = '이미 같은 시각에 잡힌 예약이 있어요. 그날 목록을 확인해 주세요.';

  static const editVisitTitle = '예약 수정';
  static const moveTogether = '같이 옮기기';
  static const moveOnlyThis = '이 방문만';

  static String moveTogetherQuestion(String names) => '$names도 같이 옮길까요?';
  static const visitTitleEn = 'Visit';
  static const visitMemoLabel = '메모';
  static const cancelReasonLabel = '취소 사유';
  static const reasonCustomerRequest = '보호자 요청';
  static const reasonShopReason = '매장 사정';
  static const previousVisitLabel = '지난 방문';
  static const groupLabel = '함께 온 아이';
  static const actionStart = '시작';
  static const actionComplete = '완료';
  static const actionCompleteNow = '바로 완료';
  static const actionCancelVisit = '취소';
  static const actionNoShow = '노쇼';
  static const actionRevert = '되돌리기';
  static const actionNextReservation = '다음 예약 잡기';
  static const completeTitle = '미용을 마쳤어요';
  static const close = '닫기';
  static const markClosedDate = '이 날 휴무로 표시';
  static const unmarkClosedDate = '휴무 해제';

  static String nextPreview(String when) => '→ $when';
  static String completeAndNextCaption(int weeks) =>
      '$weeks주 뒤 같은 요일·시간·메뉴로 채워진 예약 화면이 열려요.';
  static const cancelReasonTitle = '취소 사유를 골라 주세요';
  static const noShowConfirm = '노쇼로 기록할까요? 보호자의 노쇼 횟수에 더해져요.';

  static String noShowCount(int count) => '노쇼 $count회';

  // 확인할 것(③-B) — 서버가 판정한 항목의 글. 막지 않고 알리기만 한다.
  static const checksTitle = '확인할 것';
  static String checkCount(int count) => '확인 $count';
  static String checkCaution(String reason) => '주의 고객이에요 · $reason';
  static String checkNoShow(int count) => '지난 1년 동안 노쇼 $count번';
  static const checkFirstVisit = '처음 오는 아이예요';
  static const consentReasonSenior = '노령';
  static const consentReasonConditions = '지병';
  static String checkConsentMissing(List<String> reasons) => reasons.isEmpty
      ? '미용 동의서를 받아 주세요'
      : '미용 동의서를 받아 주세요 (${reasons.join(' · ')})';
  static String checkConsentExpired(DateTime receivedOn) =>
      '미용 동의서를 다시 받아 주세요 · 지난번 ${fullDate(receivedOn)}';
  static const consentPartBasic = '미용 안내';
  static String checkConsentPartial(List<String> parts) => parts.isEmpty
      ? '미용 동의서의 바뀐 부분만 다시 받아 주세요'
      : '미용 동의서의 바뀐 부분만 다시 받아 주세요 (${parts.join(' · ')})';
  static String checkConsentSent(String line, DateTime sentOn) =>
      '$line · ${sentOn.month}월 ${sentOn.day}일에 보냈어요';
  static String checkConditions(List<String> labels) =>
      '지병 · ${labels.join(', ')}';
  static String checkLongAbsence(int days, DateTime lastVisitOn) =>
      '$days일 만에 와요 · 지난 방문 ${lastVisitOn.month}월 ${lastVisitOn.day}일';
  static String checkConditionNote(String label, String note) =>
      '$label — $note';
  static const consentReceived = '받았어요';

  // --- 전자 동의서(⑪) ---
  static const signaturePadLabel = '서명하는 곳';
  static const signaturePadHint = '여기에 서명해 주세요';
  static const signatureAgain = '다시 쓰기';
  static String fullDate(DateTime d) => '${d.year}년 ${d.month}월 ${d.day}일';

  // 미용 동의서·주의 고객(③-B) — 반려동물 상세.
  static const groomingConsentLabel = '미용 동의서';
  static const groomingConsentNone = '받지 않았어요';
  static String groomingConsentOn(DateTime d) => '${fullDate(d)}에 받았어요';
  static const groomingConsentMore = '미용 동의서 더 보기';
  static const groomingConsentAgain = '오늘 다시 받았어요';
  static const groomingConsentClear = '받은 기록 지우기';
  static const cautionLabel = '주의 고객';
  static const cautionMark = '주의';
  static const cautionNone = '표시하지 않았어요';
  static String cautionSuggest(int noShows) => '노쇼가 $noShows번 있어요';
  static String cautionNoShowReason(int noShows) => '노쇼 $noShows번';
  static String cautionUntil(DateTime d) => '${fullDate(d)}까지 보여요';
  static const cautionSet = '표시하기';
  static const cautionMore = '주의 고객 더 보기';
  static const cautionEdit = '사유 고치기';
  static const cautionClear = '주의 표시 지우기';
  static const cautionClearConfirm = '주의 표시를 지울까요? 적어 둔 사유도 함께 지워져요.';
  static const cautionSheetTitle = '주의 고객으로 표시해요';
  static const cautionReasonHint = '사유를 한 줄로 적어 주세요';
  static const cautionSheetNote = '우리 매장에서만 보여요. 1년 뒤에 저절로 지워져요.';
  static const noShowCountLabel = '노쇼 횟수';
  static String timesCount(int count) => '$count회';

  // 보호자 계정 연결(⑦-3) — 반려동물 상세의 보호자 탭
  static const guardianLinked = '보호자 계정 연결됨';
  static String guardianLinkedOn(int month, int day) =>
      '보호자 계정 연결됨 · $month월 $day일';
  static const guardianLinkMore = '보호자 연결 더 보기';
  static const endGuardianLink = '연결 끊기';
  static const endGuardianLinkConfirm =
      '보호자가 지난 기록을 더는 볼 수 없어요. 알림장을 다시 보내면 다시 이을 수 있어요.';
  static const guardianLinkEnded = '보호자 연결을 끊었어요.';

  // 매출(⑧) — 홈의 매출 탭. 비교·목표 문장은 features/sales/state/sales_rules.dart 가 만든다.
  static const salesOwnerOnly = '매출은 사장님만 볼 수 있어요.';
  static const salesEmptyTitle = '아직 기록한 매출이 없어요';
  static const salesEmptyText = '방문을 완료하고 기록에 금액을 적으면 여기에 쌓여요.';
  static const salesSpanDay = '일';
  static const salesSpanWeek = '주';
  static const salesSpanMonth = '월';
  static const salesSpanYear = '연';
  static const salesPrev = '이전 기간';
  static const salesNext = '다음 기간';
  static const salesWonUnit = '원';
  static String salesAverage(String amount) => '한 번에 평균 $amount원';
  static const salesPayment = '결제 수단';
  static const salesPaymentNone = '미선택';
  static const salesPaymentOther = '기타';
  static const salesMenu = '메뉴';
  static const salesGuests = '손님';
  static const salesNewPets = '처음 온 아이';
  static const salesReturningPets = '다시 온 아이';
  static const salesRegulars = '단골';
  static String salesHeads(int count) => '$count마리';
  static String salesTimes(int count) => '$count번';
  static String salesCount(int count) => '$count건';
  static String salesDuePets(int count) => '다시 올 때가 지난 아이 $count마리';
  static const salesBookings = '예약';
  static const salesRemaining = '남은 예약';
  static String salesExpected(String amount) => '정가로 약 $amount';
  static const salesNoShow = '노쇼';
  static const salesCanceled = '취소';
  static const salesWeekday = '요일';
  static const salesReport = '알림장';
  static String salesReportLine(int completed, int sent, int opened) =>
      '완료한 $completed건 가운데 $sent건에 알림장을 보냈고, 보호자가 $opened건을 열어 봤어요.';
  static String salesUnrecorded(int count) => '금액을 적지 않은 완료 방문 $count건';
  static String salesBarLabel(String day, String amount) => '$day $amount원';
  // 매출에서 이어지는 화면(⑧-3)
  static const salesVisitsUnrecorded = '금액을 적지 않은 방문';
  static const salesVisitsNoShow = '노쇼한 방문';
  static const salesVisitsCanceled = '취소한 방문';
  static const salesVisitsMenu = '메뉴의 방문';
  static String salesVisitsOfMenu(String menu) => '$menu 한 방문';
  static const salesVisitsEmpty = '해당하는 방문이 없어요';
  static const salesDuePetsTitle = '다시 올 때가 지난 아이';
  static const salesDuePetsEmpty = '다시 올 때가 지난 아이가 없어요';
  static const salesToday = '오늘';
  static String salesDaysAgo(int days) => '$days일 전';
  static String salesWeeksAgo(int weeks) => '$weeks주 전';
  static const salesShowAllMenus = '모두 보기';
  static const salesSetGoal = '이번 달 목표 정하기';
  static const salesGoalTitle = '이번 달 목표';
  static const salesGoalLabel = '목표 금액';
  static const salesGoalHint = '비워 두면 목표가 없어요';
  static const salesGoalTooBig = '1억 원까지 정할 수 있어요.';
  static const salesGoalClear = '목표 지우기';
  static const salesShare = '요약 공유';
  static const salesShareFailed = '공유 화면을 열지 못했어요. 다시 시도해 주세요.';
  static const salesUnitHeads = '마리';
  static String salesVisitRowLabel(String who, String date) => '$who $date 방문 보기';
  static String salesDuePetRowLabel(String name, String since) => '$name $since';
  static String salesMenuRowLabel(String menu) => '$menu 한 방문 보기';
  static String salesFactLabel(String label, int count) => '$label $count건 보기';
  // 영문 장식(구역 이름 옆) — 화면 읽기에서는 뺀다.
  static const salesPaymentEn = 'Payment';
  static const salesMenuEn = 'Menu';
  static const salesGuestsEn = 'Guests';
  static const salesBookingsEn = 'Bookings';
  static const salesWeekdayEn = 'Weekday';
  static const salesReportEn = 'Report';
  static const dayTitleEn = 'Schedule';
  static const viewAsTimeline = '시간표로 보기';
  static const actionCompleteShort = '완료하기';
  static const markOverlap = '겹침';
  static const markUnresolved = '정리 안 됨';
  static const dayEmpty = '예약이 없어요';
  static const dayEmptyCaption = '+ 버튼으로 예약을 잡아 보세요.';
  static const closedDayNote = '휴무일';
  static const addReservation = '예약 추가';

  static String yearMonth(int year, int month) => '$year년 $month월';
  static String gapText(int minutes) => '— ${durationText(minutes)} 비어 있음 —';
  static String dayCountsText({
    required int visits,
    required int completed,
    required int inProgress,
    required int reserved,
    required int canceled,
    required int noShow,
  }) => [
    '$visits마리',
    if (completed > 0) '완료 $completed',
    if (inProgress > 0) '미용 중 $inProgress',
    if (reserved > 0) '예약 $reserved',
    if (canceled > 0) '취소 $canceled',
    if (noShow > 0) '노쇼 $noShow',
  ].join(' · ');
  static const weekdaysLong = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'];
  static const calendarWeekHeader = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  static const prevMonth = '이전 달';
  static const nextMonth = '다음 달';
  static const closedShort = '휴무';
  static String moreGroups(int count) => '외 $count건';

  static String unresolvedBanner(int count) => '정리 안 된 예약 $count건';
  static String dayHeading(int day, int weekday) =>
      '$day일 ${weekdaysLong[weekday - 1]}';
  static String previewCounts(int visits, int completed) =>
      completed > 0 ? '$visits마리 · $completed마리 완료' : '$visits마리';
  static const settingsSchedule = '일정';
  static const settingsMenus = '메뉴';
  static const opensAtLabel = '여는 시각';
  static const closesAtLabel = '닫는 시각';
  static const defaultDurationLabel = '기본 소요';
  static const closedWeekdaysLabel = '매주 쉬는 요일';
  static const closedDatesLabel = '임시 휴무';
  static const closedDateHint = 'YYYY.MM.DD';
  static const closedDateNoteHint = '메모 (선택)';
  static const addClosedDate = '휴무 추가';
  static const closedDateInvalid = '날짜를 YYYY.MM.DD 로 입력해 주세요(오늘부터).';
  static const closedDatesEmpty = '잡힌 임시 휴무가 없어요.';
  static const closesBeforeOpens = '닫는 시각은 여는 시각보다 늦어야 해요.';
  static const pickTimeTitle = '시각 고르기';
  static const confirm = '확인';
  static const hourLabel = '시';
  static const minuteLabel = '분';
  static const addMenu = '메뉴 추가';
  static const editMenu = '메뉴 수정';
  static const menuNameHint = '메뉴 이름';
  static const menuNameRequired = '메뉴 이름을 입력해 주세요.';
  static const menuDefaultDurationLabel = '기본 소요';
  static const useShopDefault = '매장 기본';
  static const archiveMenu = '보관';
  static const archiveMenuConfirm =
      '이 메뉴를 보관할까요? 지난 방문에는 남고, 새 예약에서는 고를 수 없어요.';
  static const moveUp = '위로';
  static const moveDown = '아래로';
  static const menusEmpty = '메뉴가 없어요. 메뉴 없이도 예약할 수 있어요.';
  static const menuPriceLabel = '정가';
  static const priceUnset = '가격 미정';
  static const wonUnit = '원';
  static const amountTooLarge = '1억 원까지 적을 수 있어요.';

  // 미용 기록(④)
  static const recordTitle = '미용 기록';
  static const completeRecordTitle = '완료 기록';
  static const recordPhotosLabel = '사진';
  static const addPhoto = '사진 추가';
  static const takePhoto = '사진 찍기';
  static const pickFromAlbum = '앨범에서 사진';
  static const pickVideo = '앨범에서 영상';
  static const takeVideo = '영상 찍기';
  static const videoTrimmed = '60초까지만 올릴 수 있어 앞부분 60초를 올렸어요.';
  static const videoUnsupported = '이 영상은 올릴 수 없어요.';
  static const videoTooShort = '너무 짧은 영상이에요.';
  static const phaseBefore = '전';
  static const phaseAfter = '후';
  static const addPhotoPhaseLabel = '어느 사진인가요?';
  static const uploading = '올리는 중';
  static const uploadWaiting = '대기 중';
  static const uploadStopped = '올리지 못한 사진';
  static const removeUpload = '올리기 취소';
  static const removePhoto = '사진 빼기';
  static const recordMenusLabel = '메뉴 · 금액';
  static const totalLabel = '총액';
  static const paymentLabel = '결제 수단';
  static const paymentCard = '카드';
  static const paymentCash = '현금';
  static const paymentTransfer = '계좌';
  static const careNoteLabel = '케어 메모';
  static const careNoteHint = '보호자에게 보내는 알림장에 실려요';
  static const internalNoteLabel = '내부 메모';
  static const internalNoteHint = '매장만 봐요';
  static const completeWithRecord = '완료하기';
  static const completeWithoutRecord = '나중에 적고 완료';
  static const amountHint = '금액';

  // 말로 기록하기(④-3b).
  static const micLabel = '말해서 적기';
  static const dictationUnsupported =
      '이 기기는 한국어 받아쓰기를 지원하지 않아요. 키보드의 🎤 를 써 보세요.';
  static const dictationDenied = '마이크와 음성 인식 권한이 필요해요.';
  static const dictationNoSpeech = '못 알아들었어요. 다시 말해 주세요.';
  static const dictationFailed = '받아쓰기를 이어가지 못했어요.';
  static const openSettings = '설정 열기';

  static const todayCareLabel = '오늘의 케어';
  static const editRecord = '기록 수정';
  static const writeRecord = '기록 쓰기';
  static const deleteRecord = '기록 삭제';
  static const deleteRecordConfirm =
      '이 방문의 미용 기록을 삭제할까요? 사진·메모·금액이 함께 지워지고 되돌릴 수 없어요.';

  /// '전 사진 1' — 사진 줄의 타일(접근성 이름).
  static String photoTileLabel(String phase, int index) => '$phase 사진 $index';

  /// '보호자 이수진' — 상세 넘기기 아래 줄.
  static String ownerLine(String name) => '보호자 $name';

  /// '전 사진 1 크게 보기' — 상세 넘기기의 사진(접근성 이름). 사진 줄의 이름과 겹치지 않게 한다.
  static String openPhotoLabel(String phase, int index) =>
      '$phase 사진 $index 크게 보기';

  // 피드(④-2b).
  static const viewAsCalendar = '달력으로 보기';
  static const viewAsFeed = '피드로 보기';
  static const feedTitleEn = 'Feed';
  static const feedEmpty = '아직 끝난 미용이 없어요';
  static const feedEmptyCaption = '미용을 완료하면 사진과 함께 여기에 쌓여요.';
  static String mediaCount(int n) => '사진 $n장';

  // 크게 보기(④-2b).
  static const saveOriginal = '원본 저장';
  static const toAfter = '후로 바꾸기';
  static const toBefore = '전으로 바꾸기';
  static const makeCover = '대표로';
  static const deletePhoto = '사진 삭제';
  static const deletePhotoConfirm = '이 사진을 기록에서 지울까요? 되돌릴 수 없어요.';
  static const savedToAlbum = '앨범에 저장했어요.';
  static const albumDenied = '사진 보관함 권한이 없어요. 설정에서 켜 주세요.';
  static const playVideo = '영상 재생';
  static const pauseVideo = '일시정지';

  // 미용 알림장 — 보내기 전 미리보기(⑤-3).
  static const reportPreviewTitle = '이렇게 보내요';
  static const reportMediaLabel = '사진 · 영상 — 빼려면 누르세요';
  static const reportNoMedia = '붙인 사진·영상이 없어요.';
  static const reportHiddenMark = '뺌';
  static const reportEditNote = '고치기';
  static const reportNoCareNote = '케어 메모가 없어요.';
  static const reportItemsLabel = '함께 보이는 항목';
  static const reportItemsHint = '설정에서 바꿔요';
  static const reportItemMenus = '메뉴 이름';
  static const reportItemShopInfo = '매장 정보';
  static const reportItemAmount = '금액';
  static const reportItemWeight = '몸무게';
  static const reportOpenForever = '계속 열려 있어요.';
  static const reportReflectsEdits = '보낸 뒤에 기록을 고치면 알림장에도 바로 반영돼요.';
  static const reportSend = '보내기';
  static const reportShareFailed =
      '공유 화면을 열지 못했어요. 방문 화면의 [다시 공유]로 다시 보낼 수 있어요.';

  /// '5개 중 4개' — 미리보기 머리. 전체 수 중 보호자에게 보이는 수.
  static String reportShownCount(int total, int shown) => '$total개 중 $shown개';

  /// '후 사진 1', 뺀 것은 '후 사진 1 뺌' — 미리보기 격자의 타일(접근성 이름).
  static String reportTileLabel(
    String phase,
    int index, {
    required bool hidden,
  }) => hidden
      ? '${photoTileLabel(phase, index)} $reportHiddenMark'
      : photoTileLabel(phase, index);

  /// '금액 안 보임' — 끈 항목의 칩(접근성 이름. 눈에는 줄을 그어 보인다).
  static String reportItemOff(String item) => '$item 안 보임';

  /// '10월 28일까지 열려요.'
  static String reportOpenUntil(int month, int day) => '$month월 $day일까지 열려요.';

  // 미용 알림장 — 방문 상세(⑤-3).
  static const reportLabel = '알림장';
  static const reportNotSent = '아직 안 보냄';
  static const reportNeedsRecord = '기록을 쓰면 보낼 수 있어요';

  /// 방문 상세에서 미리보기를 여는 버튼. 미리보기의 [reportSend]('보내기')가 실제로 보낸다.
  static const reportStart = '알림장 보내기';

  /// '완료 · 알림장 보냄' — 이름 카드의 상태 꼬리표 뒤에 붙는다.
  static const reportSentMark = '알림장 보냄';
  static const reportViewed = '보호자가 확인했어요';
  static const reportNotViewed = '아직 안 열었어요';
  static const reportShareAgain = '다시 공유';
  static const reportShareAgainFailed = '공유 화면을 열지 못했어요. 다시 눌러 주세요.';
  static const reportPickMedia = '보낼 사진 고르기';
  static const reportRevoke = '링크 끊기';
  static const reportRevokeConfirm = '보호자가 받은 링크가 더는 열리지 않아요.';

  // 알림톡(⑥-2) — 설정 화면.
  /// 설정 허브의 줄.
  static const settingsNotification = '알림톡';
  static const notificationSettingsTitle = '알림톡 설정';
  static const notificationOwnerOnly = '사장만 바꿀 수 있어요.';
  static const notificationOwnerLinks = '사장님이 연동할 수 있어요.';
  static const notificationPrepareTitle = '연동하기 전에 준비해 주세요';
  static const notificationPrepare1 = '카카오톡 채널을 만들어요.';
  static const notificationPrepare2 = '채널의 비즈니스 인증을 받아요. 며칠 걸려요.';
  static const notificationPrepare3 = '채널 관리자센터에서 "관리자 추가 인증"을 꺼요.';
  static const notificationSearchIdLabel = '채널 검색 아이디';
  static const notificationSearchIdHint = '@로 시작하는 아이디예요.';
  static const notificationAdminPhoneLabel = '채널 관리자 휴대폰 번호';
  static const notificationAdminPhoneHint = '이 번호의 카카오톡으로 인증번호가 와요.';
  static const notificationCategoryLabel = '업종 카테고리 코드';
  static const notificationCategoryHint = '카카오톡 채널 관리자센터에서 확인해 주세요.';
  static const notificationRequestToken = '인증번호 받기';
  static const notificationTokenLabel = '인증번호 6자리';
  static const notificationTokenHint = '관리자 카카오톡으로 보냈어요.';
  static const notificationLink = '연동하기';
  static const notificationEditInputs = '다시 입력';
  static String notificationLinkedOn(int month, int day) =>
      '연동됨 · $month월 $day일';
  static const notificationUnlink = '연동 해제';
  static const notificationUnlinkConfirm = '예정된 알림톡이 모두 취소돼요. 연동을 해제할까요?';
  static const notificationKindConfirm = '예약 접수';
  static const notificationKindReminder = '전날 리마인드';
  static const notificationKindChangeCancel = '예약 변경·취소';
  static const notificationKindReport = '알림장';
  static const notificationKindNextVisit = '다음 예약 제안';
  static const notificationTemplatePending = '심사 중이에요(보통 1~3일)';
  static const notificationTemplateApproved = '승인됨';
  static const notificationTemplateRejected = '반려됐어요 · 운영자가 확인 중';
  static const notificationReminderTimeLabel = '보내는 시각';
  static const notificationNextVisitWeeksLabel = '지난 미용 뒤';
  static String notificationWeeks(int weeks) => '$weeks주';
  static const notificationWeeksAuto = '지난 방문 간격대로';
  static const notificationCooldownLabel = '다시 보내지 않는 기간';
  static String notificationDays(int days) => '$days일';
  static const notificationNextVisitHint = '마케팅 수신에 동의한 보호자에게만 보내요.';
  static const notificationSmsFallback = '문자로 대신 보내기';
  static const notificationSmsFallbackHint =
      '알림톡을 못 받는 번호에 문자로 보내요. 문자는 알림톡보다 비싸요.';
  static String notificationSenderNumber(String number) => '발신번호 $number';
  static const notificationSenderTitle = '발신번호 인증';
  static const notificationSenderPhoneLabel = '문자를 보낼 매장 번호';
  static const notificationSenderPhoneHint = '숫자만 적어 주세요.';
  static const notificationSenderCodeLabel = '인증번호 6자리';
  static const notificationSenderConfirm = '확인';

  // 알림톡(⑥-2) — 방문 상세의 내역.
  static const notificationBlockTitle = '알림톡';
  static const notificationRowConfirm = '예약 접수';
  static const notificationRowReminder = '전날 리마인드';
  static const notificationRowReport = '알림장';
  static const notificationRowChange = '예약 변경';
  static const notificationRowCancel = '예약 취소';
  static const notificationRowNextVisit = '다음 예약 제안';
  static String notificationScheduled(String at) => '$at 예정';
  static const notificationSending = '보내는 중';
  static String notificationSent(String at) => '보냄 · $at';
  static String notificationSentBySms(String at) => '문자로 보냄 · $at';
  static const notificationFailed = '못 보냈어요';
  static const notificationFailedTransient = '잠시 문제가 있었어요';
  static const notificationFailedPermanent = '알림톡을 받을 수 없는 번호예요';
  static const notificationResend = '다시 보내기';
  static const notificationShareInstead = '다른 방법으로 보내기';

  // 알림톡(⑥-2) — 알림장 보내기 뒤.
  static const reportSentByAlimtalk = '알림톡으로 보냈어요.';
  static const reportAlimtalkFailed = '알림톡을 못 보내서 다른 방법으로 보내요.';
  static const reportAlimtalkPending = '알림톡을 보내는 중이에요.';

  // 미용 알림장 — 설정(⑤-3). 항목 이름은 미리보기의 reportItem… 을 함께 쓴다.
  /// 설정 허브의 줄.
  static const settingsReport = '알림장';
  static const reportSettingsTitle = '알림장 설정';
  static const reportSettingsOwnerOnly = '사장만 바꿀 수 있어요.';
  static const reportLinkDaysLabel = '링크가 열려 있는 기간';
  static const reportLinkDaysHint = '앞으로 보내는 알림장부터 적용돼요. 이미 보낸 알림장의 기간은 그대로예요.';
  static const reportShowItemsLabel = '알림장에 보여 줄 항목';
  static const reportShowItemsHint =
      '바꾸면 이미 보낸 알림장에도 바로 적용돼요. 사진 · 영상과 케어 메모는 늘 보이고, '
      '내부 메모와 결제 수단은 절대 보이지 않아요.';
  static const reportItemMenusHint = '기록에 적은 메뉴';
  static const reportItemAmountHint = '메뉴별 금액과 합계';
  static const reportItemWeightHint = '기록에 적은 날만 보여요';
  static const reportItemShopInfoHint = '이름 · 전화 · 주소';

  /// 링크 기간 칩 — '7일'·'30일', 기간이 없으면(null) '계속'.
  static String reportLinkDays(int? days) => days == null ? '계속' : '$days일';

  /// 35000 → '35,000원'.
  static String wonText(int amount) {
    final digits = amount.toString();
    final out = StringBuffer();
    for (var i = 0; i < digits.length; i++) {
      if (i > 0 && (digits.length - i) % 3 == 0) out.write(',');
      out.write(digits[i]);
    }
    return '$out원';
  }

  static String stepOf(int step, int total) => '$step / $total';
  static String businessHours(String opens, String closes) =>
      '영업 $opens–$closes';
  static String saveReservation(String when) => '예약 저장 · $when';
  static String monthLabel(int month) => '$month월';
  static String durationText(int minutes) {
    final h = minutes ~/ 60;
    final m = minutes % 60;
    if (h == 0) return '$m분';
    return m == 0 ? '$h시간' : '$h시간 $m분';
  }

  static String speciesLabel(String species) => switch (species) {
    'dog' => speciesDog,
    'cat' => speciesCat,
    _ => species,
  };

  static String sexLabel(String sex) => switch (sex) {
    'female' => sexFemale,
    'male' => sexMale,
    _ => sex,
  };

  /// 로그인 수단 제공자 코드를 화면에 보여줄 라벨로 바꾼다. 계정 화면과
  /// 재인증 시트(Task 16)가 함께 쓴다.
  static String providerLabel(String provider) => switch (provider) {
    'kakao' => providerKakao,
    'google' => providerGoogle,
    'apple' => providerApple,
    'dev' => providerDev,
    _ => provider,
  };

  // 기록 검색(⑨-1b). "AI"라는 말을 쓰지 않는다 — 찾아 줄 뿐이다.
  static const searchTitle = '기록 찾기';
  static const searchOpen = '기록 찾기';
  static const searchHint = '적어 둔 말로 찾아보세요';
  static const searchIntro = '기록에 적어 둔 말로 찾아보세요';
  static const searchExampleA = '예: 귀 만지면 싫어하는 아이';
  static const searchExampleB = '예: 발톱 짧게';
  static const searchEmpty = '찾은 기록이 없어요';
  static const searchNearest = '가까운 기록부터 보여 드려요';
  static String searchInPet(String name) => '$name의 기록에서';
  static const searchInThisPet = '이 아이의 기록에서';
  static const petRecordsSearch = '이 아이의 기록에서 찾기';
  static const searchKindCareNote = '케어 노트';
  static const searchKindInternalNote = '내부 메모';
  static const searchKindVisitMemo = '예약 메모';
  static const searchKindPetMemo = '특이사항';
  static const searchKindConditionNote = '지병';
  static const searchKindCustomerMemo = '보호자 메모';
  static String searchMeta(String kind, DateTime date) => '$kind · ${date.month}월 ${date.day}일';
  static String searchRowLabel(String title, String meta, String snippet) => '$title, $meta, $snippet';
}
