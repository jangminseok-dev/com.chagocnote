import 'package:flutter/material.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'app.dart';
import 'core/config/app_config.dart';
import 'design/bridge/glass_setup.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeGlass();
  final config = AppConfig.fromEnvironment();
  if (config.kakaoEnabled) {
    await KakaoSdk.init(nativeAppKey: config.kakaoNativeAppKey);
  }
  runApp(buildRoot());
}
