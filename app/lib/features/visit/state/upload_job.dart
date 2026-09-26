import '../api/record_models.dart';

/// 사진 한 장(또는 영상 한 편)이 기록에 붙기까지의 단계(설계 10.2).
///
/// 영상의 [preparing]은 압축·포스터를 만드는 중이다(④-3a 설계 4.2).
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
    this.stoppedCode,
    this.kind = MediaKind.photo,
    this.durationSeconds,
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
        // 이 칸이 생기기 전에 저장된 항목에는 없다 — 멈추지 않은 것으로 읽는다.
        stoppedCode: json['stopped_code'] as String?,
        // 영상이 생기기 전에 저장된 항목에는 없다 — 사진으로 읽는다.
        kind: MediaKind.fromCode(json['kind'] as String? ?? 'photo'),
        durationSeconds: json['duration_seconds'] as int?,
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

  /// 사진이면 렌디션 셋, 영상이면 압축본(mp4)·포스터 둘을 올린다.
  final MediaKind kind;

  /// 압축본의 길이(초). 영상만.
  final int? durationSeconds;

  /// 다시 해도 안 되는 실패로 멈췄으면 그 오류 코드(예: `MEDIA_LIMIT_EXCEEDED`). 멈춘 항목은 스스로 다시
  /// 하지 않고, 사용자가 [다시 시도]하거나 [올리기 취소]할 때까지 파일과 함께 남는다(오류 화면 다듬기
  /// 설계 4절). 기기에 남긴다.
  final String? stoppedCode;

  bool get stopped => stoppedCode != null;

  // 아래 셋은 기기에 남기지 않는다(다시 켜면 처음부터 센다).

  /// 올리기 진행률 0~1.
  final double progress;

  /// 연달아 실패한 횟수. 다시 시도 간격을 정한다.
  final int failures;

  /// 지금 올리는 중.
  final bool running;

  /// 실패한 뒤 다시 시도를 기다리는 중 — 타일은 "대기 중"과 [올리기 취소]만 보인다.
  bool get waiting => failures > 0 && !running && !stopped;

  String? get originalPath => dir == null ? null : '$dir/original.jpg';
  String? get displayPath => dir == null ? null : '$dir/display.jpg';
  String? get thumbPath => dir == null ? null : '$dir/thumb.jpg';

  /// 영상의 압축본. 포스터는 [thumbPath]다.
  String? get videoPath => dir == null ? null : '$dir/video.mp4';

  UploadJob copyWith({
    UploadStage? stage,
    String? dir,
    int? width,
    int? height,
    int? Function()? mediaId,
    double? progress,
    int? failures,
    bool? running,
    String? Function()? stoppedCode,
    int? Function()? durationSeconds,
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
    stoppedCode: stoppedCode == null ? this.stoppedCode : stoppedCode(),
    kind: kind,
    durationSeconds: durationSeconds == null
        ? this.durationSeconds
        : durationSeconds(),
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
    'stopped_code': stoppedCode,
    'kind': kind.code,
    'duration_seconds': durationSeconds,
  };
}
