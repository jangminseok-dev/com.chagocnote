import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 설계 6.2: 글래스는 떠 있는 조작 계층(탭바 등)에만 쓰고, 스크롤 콘텐츠에는
/// 쓰지 않는다(최종 검토 D). 스크롤 목록 행은 `AppCard`(불투명)를 쓴다.
void main() {
  test('스크롤 목록 화면은 AppGlassCard·GlassSurface 를 쓰지 않는다', () {
    const scrollScreens = [
      'lib/features/shop/screens/members_screen.dart',
      'lib/features/auth/screens/shop_select_screen.dart',
      'lib/features/account/screens/account_screen.dart',
      'lib/features/customer/screens/pet_detail_screen.dart',
      'lib/features/customer/screens/customer_list_tab.dart',
      'lib/features/customer/screens/family_card_view.dart',
      'lib/features/customer/screens/pet_form.dart',
      'lib/features/customer/screens/pet_form_screen.dart',
      'lib/features/customer/screens/customer_form.dart',
      'lib/features/customer/screens/customer_edit_screen.dart',
      'lib/features/customer/screens/register_customer_screen.dart',
      'lib/features/visit/screens/visit_form.dart',
      'lib/features/visit/screens/register_visit_screen.dart',
    ];
    final violations = [
      for (final path in scrollScreens)
        if (File(
          path,
        ).readAsStringSync().contains(RegExp(r'AppGlassCard|GlassSurface')))
          path,
    ];

    expect(violations, isEmpty, reason: '스크롤 목록에 글래스를 씀: $violations');
  });
}
