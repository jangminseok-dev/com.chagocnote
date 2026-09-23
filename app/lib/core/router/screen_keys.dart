import 'package:flutter/material.dart';

/// 라우터가 어떤 화면에 도달했는지 테스트에서 식별하기 위한 키. 실제 화면의
/// 루트 위젯이 이 키를 갖는다(자리 표시 화면이었을 때와 동일한 키를 유지).
class ScreenKeys {
  static const splash = Key('screen_splash');
  static const login = Key('screen_login');
  static const invite = Key('screen_invite');
  static const shopSelect = Key('screen_shop_select');
  static const home = Key('screen_home');
  static const settings = Key('screen_settings');
  static const settingsMembers = Key('screen_settings_members');
  static const settingsShop = Key('screen_settings_shop');
  static const settingsSchedule = Key('screen_settings_schedule');
  static const settingsMenus = Key('screen_settings_menus');
  static const settingsAccount = Key('screen_settings_account');
  static const settingsAccountWithdraw = Key('screen_settings_account_withdraw');
  static const registerCustomer = Key('screen_register_customer');
  static const customerEdit = Key('screen_customer_edit');
  static const petForm = Key('screen_pet_form');
  static const petDetail = Key('screen_pet_detail');
  static const registerVisit = Key('screen_register_visit');
  static const visitDraft = Key('screen_visit_draft');
  static const visitEdit = Key('screen_visit_edit');
  static const visitDetail = Key('screen_visit_detail');
  static const day = Key('screen_day');
}
