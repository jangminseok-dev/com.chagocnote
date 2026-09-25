import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

/// 업로드 대기열이 렌디션 파일과 대기열 기록을 두는 앱 전용 폴더(설계 10.2).
///
/// 캐시 폴더가 아니라 지원 폴더다 — 운영체제가 공간이 모자라다고 지우면 올리기 전 사진이 사라진다.
final uploadsDirProvider = FutureProvider<Directory>((ref) async {
  final base = await getApplicationSupportDirectory();
  return Directory('${base.path}/uploads').create(recursive: true);
});
