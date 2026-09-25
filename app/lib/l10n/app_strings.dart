/// 앱 전체에서 쓰는 사용자 노출 문자열. 전부 한국어다.
///
/// 화면은 이 파일의 상수만 쓰고, 문자열을 직접 쓰지 않는다. 오류 문구는
/// `messageFor`(`core/error/error_messages.dart`)를 대신 쓴다.
class AppStrings {
  const AppStrings._();

  static const appName = '차곡노트';
  static const retry = '다시 시도';
  static const back = '뒤로';

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
  static const comingSoonEmptyTitle = '준비 중입니다';
  static const comingSoonSheetText = '매출은 다음 업데이트에서 만나요';

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
  static const saved = '저장했습니다';
  static const shopNameRequired = '매장 이름을 입력해 주세요.';

  // 계정
  static const providerKakao = '카카오';
  static const providerGoogle = 'Google';
  static const providerApple = 'Apple';
  static const providerDev = '개발용';
  static const accountLinkedMethods = '로그인 수단';
  static const accountAddMethod = '로그인 수단 추가';
  static const unlink = '해제';
  static const unlinkOnlyOneCaption = '마지막 로그인 수단은 해제할 수 없습니다.';
  static const unlinkConfirmMessage = '해제하면 다른 모든 기기에서 로그아웃됩니다.';
  static const withdraw = '회원 탈퇴';

  // 재인증
  static const reauthPromptTitle = '보안을 위해 다시 로그인해 주세요';
  static const reauthMismatch = '다른 계정입니다. 이 계정에 연결된 로그인 수단으로 다시 로그인해 주세요.';

  // 회원 탈퇴
  static const withdrawNoticeIrreversible = '되돌릴 수 없습니다.';
  static const withdrawNoticeShopRecordsStay = '매장의 기록은 매장에 남습니다.';
  static const withdrawNoticeMembershipGone = '소속과 초대 코드는 사라집니다.';
  static const withdrawNoticeNewAccount = '같은 소셜 계정으로 다시 가입하면 새 계정이 됩니다.';
  static const withdrawConfirmCheckbox = '안내를 확인했습니다';
  static const withdrawSubmit = '탈퇴하기';
  static const withdrawShopCloseTitle = '혼자 운영하는 매장도 함께 닫힙니다';
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
  static const passedAwayBadge = '무지개다리';
  static const markPassedAway = '무지개다리 표시';
  static const unmarkPassedAway = '무지개다리 되돌리기';
  static const markPassedAwayConfirm = '무지개다리를 건넜다고 표시할까요? 목록에서 숨겨지고 기록은 남습니다.';
  static const deletePet = '반려동물 삭제';
  static const deletePetConfirm = '잘못 등록한 반려동물을 삭제할까요? 질병 기록도 함께 지워지고 되돌릴 수 없습니다.';
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
  static const dogBreeds = ['말티즈', '푸들', '포메라니안', '비숑', '시츄', '요크셔테리어', '치와와', '믹스'];
  static const catBreeds = ['코리안 숏헤어', '러시안 블루', '페르시안', '브리티시 숏헤어', '스코티시 폴드', '믹스'];

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
  static const deleteCustomerConfirm = '고객을 삭제할까요? 보호자의 이름·전화번호·메모와 반려동물의 이름·질병 기록이 지워지고 되돌릴 수 없습니다.';

  static const registerCustomer = '고객 등록';
  static const registerStepPhone = '전화번호';
  static const registerStepOwner = '보호자';
  static const registerStepPet = '반려동물';
  static const next = '다음';
  static const addPetToExisting = '이 보호자에게 반려동물 추가';

  static String registerStepTitle(String step, int index) => '$step $index / 3';
  static String lookupFound(String name, List<String> petNames) => petNames.isEmpty
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
  static const noShowConfirm = '노쇼로 기록할까요? 보호자의 노쇼 횟수에 더해집니다.';

  static String noShowCount(int count) => '노쇼 $count회';
  static const noShowCountLabel = '노쇼 횟수';
  static String timesCount(int count) => '$count회';
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
  static String dayHeading(int day, int weekday) => '$day일 ${weekdaysLong[weekday - 1]}';
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
  static const archiveMenuConfirm = '이 메뉴를 보관할까요? 지난 방문에는 남고, 새 예약에서는 고를 수 없어요.';
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
  static const takePhoto = '카메라';
  static const pickFromAlbum = '앨범';
  static const phaseBefore = '전';
  static const phaseAfter = '후';
  static const addPhotoPhaseLabel = '어느 사진인가요?';
  static const uploading = '올리는 중';
  static const uploadWaiting = '대기 중';
  static const removeUpload = '빼기';
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

  static const todayCareLabel = '오늘의 케어';
  static const editRecord = '기록 수정';
  static const writeRecord = '기록 쓰기';
  static const deleteRecord = '기록 삭제';
  static const deleteRecordConfirm = '이 방문의 미용 기록을 삭제할까요? 사진·메모·금액이 함께 지워지고 되돌릴 수 없습니다.';

  /// '전 사진 1' — 사진 줄의 타일(접근성 이름).
  static String photoTileLabel(String phase, int index) => '$phase 사진 $index';

  /// '보호자 이수진' — 상세 넘기기 아래 줄.
  static String ownerLine(String name) => '보호자 $name';

  /// '전 사진 1 크게 보기' — 상세 넘기기의 사진(접근성 이름). 사진 줄의 이름과 겹치지 않게 한다.
  static String openPhotoLabel(String phase, int index) =>
      '$phase 사진 $index 크게 보기';

  // 크게 보기(④-2b).
  static const saveOriginal = '원본 저장';
  static const toAfter = '후로 바꾸기';
  static const toBefore = '전으로 바꾸기';
  static const makeCover = '대표로';
  static const deletePhoto = '사진 삭제';
  static const deletePhotoConfirm = '이 사진을 기록에서 지울까요? 되돌릴 수 없습니다.';
  static const savedToAlbum = '앨범에 저장했어요.';
  static const albumDenied = '사진 보관함 권한이 없어요. 설정에서 켜 주세요.';

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
  static String businessHours(String opens, String closes) => '영업 $opens–$closes';
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
}
