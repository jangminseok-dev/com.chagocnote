import 'package:dio/dio.dart';

import '../error/api_exception.dart';
import '../storage/token_store.dart';

/// 액세스 토큰 부착, 401 발생 시 단일 비행(single-flight) 리프레시,
/// 원 요청 1회 재시도를 담당하는 HTTP 클라이언트.
///
/// 리프레시 요청은 별도의 "민짜" [Dio] 인스턴스로 보낸다. 같은 인터셉터를
/// 태우면 리프레시 요청 자체가 401을 받았을 때 다시 리프레시를 시도하는
/// 재귀에 빠질 수 있기 때문이다.
class ApiClient {
  ApiClient({
    required this._tokenStore,
    String baseUrl = '',
    this._onSessionEnded,
    Dio? dio,
    Dio? refreshDio,
  })  : _dio = dio ?? Dio(BaseOptions(baseUrl: baseUrl)),
        _refreshDio = refreshDio ?? Dio(BaseOptions(baseUrl: baseUrl)) {
    _dio.interceptors.add(
      InterceptorsWrapper(onRequest: _onRequest, onError: _onError),
    );
  }

  final TokenStore _tokenStore;
  final void Function()? _onSessionEnded;
  final Dio _dio;
  final Dio _refreshDio;

  /// 진행 중인 리프레시. 동시에 여러 요청이 401을 받아도 리프레시는
  /// 하나만 나가도록(single-flight) 이 필드를 공유한다.
  Future<void>? _refreshFuture;

  static const _gatewayFailures = {502, 503, 504};

  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    bool public = false,
  }) =>
      _send('GET', path, queryParameters: queryParameters, public: public);

  Future<dynamic> post(String path, {Object? data, bool public = false}) =>
      _send('POST', path, data: data, public: public);

  Future<dynamic> put(String path, {Object? data, bool public = false}) =>
      _send('PUT', path, data: data, public: public);

  Future<dynamic> patch(String path, {Object? data, bool public = false}) =>
      _send('PATCH', path, data: data, public: public);

  Future<dynamic> delete(String path, {Object? data, bool public = false}) =>
      _send('DELETE', path, data: data, public: public);

  Future<dynamic> _send(
    String method,
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    bool public = false,
  }) async {
    try {
      final response = await _dio.request<dynamic>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(method: method, extra: {'public': public}),
      );
      return response.data;
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final isPublic = options.extra['public'] == true;
    if (!isPublic) {
      final access = await _tokenStore.readAccess();
      if (access != null) {
        options.headers['Authorization'] = 'Bearer $access';
      }
    }
    handler.next(options);
  }

  Future<void> _onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    final isPublic = options.extra['public'] == true;
    final alreadyRetried = options.extra['_retried'] == true;
    final apiError = _toApiException(err);
    final isUnauthenticated =
        err.response?.statusCode == 401 && apiError.code == 'UNAUTHENTICATED';

    if (isPublic || alreadyRetried || !isUnauthenticated) {
      handler.reject(err.copyWith(error: apiError));
      return;
    }

    try {
      await _ensureRefreshed();
    } on ApiException catch (refreshError) {
      handler.reject(err.copyWith(error: refreshError));
      return;
    }

    options.extra['_retried'] = true;
    try {
      final retried = await _dio.fetch<dynamic>(options);
      handler.resolve(retried);
    } on DioException catch (retryErr) {
      handler.reject(retryErr.copyWith(error: _toApiException(retryErr)));
    }
  }

  /// 진행 중인 리프레시가 있으면 그것을 기다리고, 없으면 새로 시작한다.
  Future<void> _ensureRefreshed() {
    final existing = _refreshFuture;
    if (existing != null) return existing;

    final future = _performRefresh();
    _refreshFuture = future;
    // `whenComplete`이 만드는 파생 Future는 아무도 await하지 않는다. 원본
    // `future`의 에러는 다른 곳(각 요청의 catch)에서 이미 처리되므로,
    // 이 파생 Future에 `ignore()`를 걸어 두 번째 "처리되지 않은 예외"로
    // 잡히는 것을 막는다.
    future.whenComplete(() {
      if (identical(_refreshFuture, future)) {
        _refreshFuture = null;
      }
    }).ignore();
    return future;
  }

  Future<void> _performRefresh() async {
    final refreshToken = await _tokenStore.readRefresh();
    if (refreshToken == null) {
      // 지울 세션도, 끝낼 세션도 없다 — 이미 로그아웃됐거나(다른 요청의 갱신
      // 실패, 로그아웃, 탈퇴 등) 애초에 로그인한 적이 없다. 여기서
      // clear()·onSessionEnded 를 또 부르면, 이미 끝난 세션 뒤에 뒤늦게
      // 도착한 요청마다 "다시 로그인" 안내가 반복해서 뜬다.
      throw ApiException(
        statusCode: 401,
        code: 'UNAUTHENTICATED',
        message: '리프레시 토큰이 없습니다.',
      );
    }

    try {
      final response = await _refreshDio.post<Map<String, dynamic>>(
        '/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final body = response.data!;
      // 갱신이 오가는 동안 다른 경로(로그아웃, 해제, 탈퇴 등)로 이 기기의
      // 세션이 이미 끝났을 수 있다. 그 경우 저장소의 리프레시 토큰은 이번
      // 갱신에 쓴 토큰과 달라져(대개 null로) 있다. 이를 보지 않고 새 토큰을
      // 저장하면 이미 끝난 세션이 되살아난다 — 저장하지 않는다. 세션을
      // 끝낸 쪽이 onSessionEnded 를 이미 불렀을 것이므로 여기서는 다시
      // 부르지 않고, 원 요청도 재시도하지 않는다.
      final currentRefresh = await _tokenStore.readRefresh();
      if (currentRefresh != refreshToken) {
        throw ApiException(
          statusCode: 401,
          code: 'UNAUTHENTICATED',
          message: '갱신 중 세션이 종료되었습니다.',
        );
      }
      await _tokenStore.save(
        access: body['access_token'] as String,
        refresh: body['refresh_token'] as String,
      );
    } on DioException catch (e) {
      final apiError = ApiException.fromDioException(e);
      // 요청이 백엔드에 닿지 못한 실패(연결·타임아웃, 게이트웨이의 502·503·504)는
      // 토큰이 아직 소모되지 않았을 가능성이 높다. 토큰을 남겨 두고, 사용자가 다음에
      // 직접 일으킨 요청에서 한 번 더 시도하게 한다. 여기서 자동으로 다시 보내지는 않는다.
      final reachedBackend = !apiError.isNetwork &&
          !_gatewayFailures.contains(apiError.statusCode);
      if (!reachedBackend) {
        throw apiError;
      }

      // 이 갱신이 오가는 동안 다른 경로(로그인 수단 해제 등)가 이미 새
      // 토큰을 저장했을 수 있다(fix round 1 — Task 12 검토에서 드러남).
      // 그 경우 이 갱신의 실패는 이미 죽은 옛 리프레시 토큰에 대한
      // 것일 뿐, 이 기기의 세션은 그 다른 경로가 저장한 새 토큰으로
      // 이미 살아 있다. 비교 없이 지우면 방금 끝난 다른 작업이 만든
      // 세션을 도로 로그아웃시키는 꼴이 된다. 지우지도, 세션 종료를
      // 알리지도 않고 이 죽은 갱신 시도만 조용히 끝낸다 — 아직 재시도
      // 전인 원 요청은 (호출부의 기존 로직대로) 저장소의 새 액세스
      // 토큰으로 한 번 재시도된다.
      final currentRefresh = await _tokenStore.readRefresh();
      if (currentRefresh != refreshToken) {
        return;
      }

      // 서버가 거절했거나(401·403, 재사용 감지 포함) 처리 중 실패했다(500 — 토큰이 이미
      // 소모됐을 수 있다). 이 기기의 토큰을 버리고 세션 종료를 알린다.
      await _tokenStore.clear();
      _onSessionEnded?.call();
      throw apiError;
    }
  }

  ApiException _toApiException(DioException e) {
    final error = e.error;
    if (error is ApiException) return error;
    return ApiException.fromDioException(e);
  }
}
