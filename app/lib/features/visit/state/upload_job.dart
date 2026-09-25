import '../api/record_models.dart';

/// 사진 한 장이 기록에 붙기까지의 단계(설계 10.2).
enum UploadStage {
  /// 렌디션을 만드는 중. 기기에 남기지 않는다 — 앱이 꺼지면 고른 원본부터 다시 골라야 한다.
  preparing,

  /// 렌디션 셋이 앱 폴더에 있다. 다음은 발급 → 올리기 셋 → 확인.
  prepared,

  /// 서버가 사진을 확인했다([UploadJob.mediaId]). 다음은 덧붙이기.
  confirmed,
}

/// 업로드 대기열의 항목 하나. 기록에 붙으면 대기열에서 빠지고 로컬 파일도 지운다.
class UploadJob {
  const UploadJob({
    required this.id,
    required this.userId,
    required this.shopId,
    required this.visitId,
    required this.phase,
    required this.stage,
    this.dir,
    this.width = 0,
    this.height = 0,
    this.mediaId,
    this.progress = 0,
    this.failures = 0,
    this.running = false,
  });

  /// 폴더는 업로드 폴더 [root] 아래 항목 ID 다 — iOS 는 앱 폴더의 절대 경로가 실행마다 바뀔 수 있어
  /// 경로를 남기지 않고 읽을 때 다시 잇는다.
  factory UploadJob.fromJson(Map<String, dynamic> json, String root) =>
      UploadJob(
        id: json['id'] as String,
        userId: json['user_id'] as int,
        shopId: json['shop_id'] as int,
        visitId: json['visit_id'] as int,
        phase: MediaPhase.fromCode(json['phase'] as String),
        stage: UploadStage.values.byName(json['stage'] as String),
        dir: '$root/${json['id']}',
        width: json['width'] as int,
        height: json['height'] as int,
        mediaId: json['media_id'] as int?,
      );

  final String id;

  /// 대기열은 로그인한 사용자의 것이다 — 다른 사람이 로그인하면 지운다.
  final int userId;
  final int shopId;
  final int visitId;
  final MediaPhase phase;
  final UploadStage stage;

  /// 렌디션 셋이 있는 폴더. [UploadStage.preparing]이면 null.
  final String? dir;
  final int width;
  final int height;
  final int? mediaId;

  // 아래 셋은 기기에 남기지 않는다(다시 켜면 처음부터 센다).

  /// 올리기 진행률 0~1.
  final double progress;

  /// 연달아 실패한 횟수. 다시 시도 간격을 정한다.
  final int failures;

  /// 지금 올리는 중.
  final bool running;

  /// 실패한 뒤 다시 시도를 기다리는 중 — 타일은 "대기 중"과 [빼기]만 보인다.
  bool get waiting => failures > 0 && !running;

  String? get originalPath => dir == null ? null : '$dir/original.jpg';
  String? get displayPath => dir == null ? null : '$dir/display.jpg';
  String? get thumbPath => dir == null ? null : '$dir/thumb.jpg';

  UploadJob copyWith({
    UploadStage? stage,
    String? dir,
    int? width,
    int? height,
    int? Function()? mediaId,
    double? progress,
    int? failures,
    bool? running,
  }) => UploadJob(
    id: id,
    userId: userId,
    shopId: shopId,
    visitId: visitId,
    phase: phase,
    stage: stage ?? this.stage,
    dir: dir ?? this.dir,
    width: width ?? this.width,
    height: height ?? this.height,
    mediaId: mediaId == null ? this.mediaId : mediaId(),
    progress: progress ?? this.progress,
    failures: failures ?? this.failures,
    running: running ?? this.running,
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'shop_id': shopId,
    'visit_id': visitId,
    'phase': phase.code,
    'stage': stage.name,
    'width': width,
    'height': height,
    'media_id': mediaId,
  };
}
