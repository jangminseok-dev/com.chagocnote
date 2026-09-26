import '../../../core/proxy/api_client.dart';

/// 올릴 곳 — 서명 PUT URL. 사진은 셋, 영상은 원본·포스터 둘([display]가 null).
class UploadTargets {
  const UploadTargets({
    required this.original,
    required this.display,
    required this.thumb,
  });

  factory UploadTargets.fromJson(Map<String, dynamic> json) => UploadTargets(
    original: json['original'] as String,
    display: json['display'] as String?,
    thumb: json['thumb'] as String,
  );

  final String original;
  final String? display;
  final String thumb;
}

/// 발급 응답. URL 은 [expiresAt]까지(15분) 쓸 수 있다.
class IssuedUpload {
  const IssuedUpload({
    required this.mediaId,
    required this.puts,
    required this.expiresAt,
  });

  factory IssuedUpload.fromJson(Map<String, dynamic> json) => IssuedUpload(
    mediaId: json['media_id'] as int,
    puts: UploadTargets.fromJson(json['puts'] as Map<String, dynamic>),
    expiresAt: DateTime.parse(json['expires_at'] as String),
  );

  final int mediaId;
  final UploadTargets puts;
  final DateTime expiresAt;
}

/// 미디어 발급·확인 API(설계 7.1). 올리기 자체는 `UploadClient`가 서명 URL 로 한다.
class MediaApi {
  MediaApi(this._client);

  final ApiClient _client;

  /// 사진 하나를 올릴 자리를 받는다. [byteSize]는 원본 렌디션의 바이트 수.
  Future<IssuedUpload> issuePhoto(
    int shopId, {
    required int byteSize,
    required int width,
    required int height,
  }) async => IssuedUpload.fromJson(
    await _client.post(
          '/v1/shops/$shopId/media/uploads',
          data: {
            'kind': 'photo',
            'content_type': 'image/jpeg',
            'byte_size': byteSize,
            'width': width,
            'height': height,
          },
        )
        as Map<String, dynamic>,
  );

  /// 영상 하나를 올릴 자리를 받는다. 압축본(mp4)의 바이트 수·가로·세로·길이(초).
  Future<IssuedUpload> issueVideo(
    int shopId, {
    required int byteSize,
    required int width,
    required int height,
    required int durationSeconds,
  }) async => IssuedUpload.fromJson(
    await _client.post(
          '/v1/shops/$shopId/media/uploads',
          data: {
            'kind': 'video',
            'content_type': 'video/mp4',
            'byte_size': byteSize,
            'width': width,
            'height': height,
            'duration_seconds': durationSeconds,
          },
        )
        as Map<String, dynamic>,
  );

  /// 다 올렸다고 알린다. 서버가 객체를 확인하면 기록에 붙일 수 있다.
  Future<void> confirm(int shopId, int mediaId) async {
    await _client.post('/v1/shops/$shopId/media/$mediaId/confirm');
  }
}
