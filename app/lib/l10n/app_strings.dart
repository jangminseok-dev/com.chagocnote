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
  static const calendarEmptyTitle = '아직 기록이 없습니다';
  static const calendarEmptyCaption = '예약을 만들면 여기에서 모아 볼 수 있어요.';
  static const comingSoonEmptyTitle = '준비 중입니다';
  static const comingSoonSheetText = '예약과 기록은 다음 업데이트에서 만나요';

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
  static const includePassed = '무지개다리 포함';
  static const customerSearchHint = '번호 뒷자리, 이름, 반려동물 (초성 가능)';
  static const customersEmpty = '등록된 고객이 없어요';
  static const customersEmptyCaption = '+ 버튼으로 첫 고객을 등록해 보세요.';
  static const customersNoMatch = '찾는 고객이 없어요';
  static const conditionsBadge = '질병';

  static String petCountText(int count) => '$count마리';

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
