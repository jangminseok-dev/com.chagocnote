import 'api_exception.dart';

/// 오류의 원인 — 문구와 화면이 보일 행동(다시 시도·돌아가기·스스로 잇기)을 정한다(오류 화면 다듬기 설계 2절).
enum ErrorKind {
  /// 인터넷이 없거나 서버에 닿지 못했다. 인터넷이 돌아오면 스스로 다시 한다.
  offline,

  /// 서버가 5xx 이거나 형식을 모르는 응답을 줬다(게이트웨이 502·503 등).
  server,

  /// 403 — 다시 해도 같다.
  denied,

  /// 404 — 이미 지워졌을 수 있다. 다시 해도 같다.
  gone,

  /// 그 밖(업무 규칙 4xx, `ApiException`이 아닌 오류).
  other;

  /// 다시 해 볼 만한가 — 권한·없음은 다시 해도 같으니 [다시 시도] 대신 [돌아가기]를 준다.
  bool get retryable => this != denied && this != gone;
}

/// [error]의 원인. 기준은 `ApiException`의 코드와 상태 번호뿐이다.
ErrorKind kindOf(Object error) {
  if (error is! ApiException) return ErrorKind.other;
  if (error.isNetwork) return ErrorKind.offline;
  final status = error.statusCode;
  if ((status != null && status >= 500) || error.code == 'HTTP_ERROR') {
    return ErrorKind.server;
  }
  if (status == 403) return ErrorKind.denied;
  if (status == 404) return ErrorKind.gone;
  return ErrorKind.other;
}
