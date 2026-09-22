import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 오늘 날짜. 테스트·골든이 고정된 날짜로 오버라이드할 수 있도록
/// provider로 둔다.
final todayProvider = Provider<DateTime>((ref) => DateTime.now());
