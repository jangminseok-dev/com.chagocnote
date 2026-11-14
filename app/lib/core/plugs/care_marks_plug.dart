import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 미용 동의·주의 표시가 바뀌었음을 알리는 자리(③-B) — 방문의 "확인할 것"이 낡는데 customer 는
/// visit 를 import 하지 않는다(기능 폴더 규칙). `app.dart`의 `buildRoot`가 visit 의 읽기를
/// 무효화하도록 채운다. 채우지 않으면(테스트) 아무것도 하지 않는다.
typedef CareMarksChanged = void Function();

final careMarksChangedPlugProvider = Provider<CareMarksChanged>((ref) => () {});
