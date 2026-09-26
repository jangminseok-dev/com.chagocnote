import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/error/error_kind.dart';
import '../../../core/proxy/app_dirs.dart';
import '../../../core/proxy/network_watcher.dart';
import '../../../core/proxy/photo_renditions.dart';
import '../../../core/proxy/providers.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../auth/state/shop_scoped.dart';
import '../../auth/state/shop_selection.dart';
import '../../customer/state/customer_list_controller.dart';
import '../../customer/state/customer_providers.dart';
import '../api/record_models.dart';
import 'feed_controller.dart';
import 'upload_job.dart';
import 'upload_store.dart';
import 'visit_providers.dart';

/// 다시 시도 예약 — 테스트가 바꿔 끼워 시간을 건너뛴다.
typedef RetryScheduler = Timer Function(Duration delay, void Function() run);

final uploadRetrySchedulerProvider = Provider<RetryScheduler>(
  (ref) => Timer.new,
);

/// 다시 해도 안 되는 실패인가 — 권한·없음·업무 규칙 4xx(한도 초과·형식·크기·방문 삭제 등). 인터넷·서버
/// 오류와 세션 만료(401)·잦은 시도(429)는 다시 해 볼 만하다(오류 화면 다듬기 설계 4절).
bool stopsUpload(Object error) {
  if (error is! ApiException) return false;
  final status = error.statusCode;
  return switch (kindOf(error)) {
    ErrorKind.denied || ErrorKind.gone => true,
    ErrorKind.other =>
      status != null && status >= 400 && status < 500 && status != 401 && status != 429,
    ErrorKind.offline || ErrorKind.server => false,
  };
}

/// [failures]번 연달아 실패한 뒤 다시 시도까지 — 1·2·4… 초, 최대 5분(설계 10.2).
Duration retryDelay(int failures) =>
    Duration(seconds: min(300, 1 << min(failures - 1, 9)));

/// 사진 업로드 대기열(설계 10.2) — 사진이 사라지지 않는 것이 이 앱의 첫째 약속이다.
///
/// 사진을 고르면 곧바로 렌디션 셋을 앱 폴더에 쓰고 항목을 기기에 남긴다. 그다음 발급 → 올리기 셋 →
/// 확인 → 덧붙이기를 한 장씩 차례로 한다. 앱이 꺼졌다 켜지면 남은 단계부터, 실패하면 간격을 늘려
/// 스스로, 인터넷이 돌아오면 바로 다시 한다. 서명 URL 이 만료됐거나(15분) 서버가 붙지 않은 사진을
/// 정리했으면(하루) 로컬 파일로 발급부터 다시 한다. 사용자가 빼면 취소하고(`CANCELLED`, 문구 없음)
/// 파일을 지운다.
///
/// 대기열은 로그인한 사용자의 것이다. 로그아웃·탈퇴하면 전부 지우고, 다른 사람이 로그인하면 그
/// 사람 것이 아닌 항목을 지운다. 세션 만료로 로그아웃되면 남겨 둔다 — 같은 사람이 다시 로그인하면
/// 이어 간다.
class UploadQueue extends AsyncNotifier<List<UploadJob>> {
  late UploadStore _store;
  final _tokens = <String, CancelToken>{};
  final _timers = <String, Timer>{};
  bool _pumping = false;
  Future<void> _saving = Future.value();
  int _seq = 0;

  List<UploadJob> get _jobs => state.value ?? const [];

  @override
  Future<List<UploadJob>> build() async {
    _store = UploadStore(await ref.read(uploadsDirProvider.future));
    var jobs = await _store.load();
    final session = ref.read(sessionControllerProvider).value;
    if (session is SignedIn) jobs = _ownedBy(session.me, jobs);
    await _store.save(jobs);
    await _store.deleteOrphans(jobs);

    ref.listen(
      sessionControllerProvider,
      (previous, next) => _onSession(previous?.value, next.value),
    );
    final restored = ref
        .read(networkWatcherProvider)
        .restored
        .listen((_) => retryNow());
    ref.onDispose(() {
      restored.cancel();
      for (final t in _timers.values) {
        t.cancel();
      }
      for (final t in _tokens.values) {
        t.cancel();
      }
    });
    Future.microtask(_pump);
    return jobs;
  }

  /// 고른 사진을 대기열에 넣는다. 타일은 곧바로 나오고(렌디션을 만드는 중), 파일이 준비되는 대로 올린다.
  Future<void> addPhotos({
    required int shopId,
    required int visitId,
    required MediaPhase phase,
    required List<String> sources,
  }) async {
    await future;
    final userId = ref.read(currentUserIdProvider);
    if (userId == null || sources.isEmpty) return;
    final fresh = [
      for (final _ in sources)
        UploadJob(
          id: '${DateTime.now().microsecondsSinceEpoch}-${_seq++}',
          userId: userId,
          shopId: shopId,
          visitId: visitId,
          phase: phase,
          stage: UploadStage.preparing,
        ),
    ];
    _set([..._jobs, ...fresh]);
    final maker = ref.read(photoRenditionMakerProvider);
    for (var i = 0; i < fresh.length; i++) {
      final id = fresh[i].id;
      final dir = Directory(_dirOf(id));
      try {
        final made = await maker.make(sources[i], dir);
        if (!ref.mounted) return;
        if (!_has(id)) {
          await _store.deleteDir(dir.path);
          continue;
        }
        _update(
          id,
          (j) => j.copyWith(
            stage: UploadStage.prepared,
            dir: dir.path,
            width: made.width,
            height: made.height,
          ),
        );
        await _persist();
        unawaited(_pump());
      } catch (_) {
        if (!ref.mounted) return;
        // 읽을 수 없는 파일(깨진 사진 등)은 올릴 수 없다 — 대기열에서 뺀다.
        _set([
          for (final j in _jobs)
            if (j.id != id) j,
        ]);
        await _store.deleteDir(dir.path);
      }
    }
  }

  /// [올리기 취소] — 올리는 중이면 취소한다. 취소는 오류가 아니라 아무 문구도 없다.
  Future<void> remove(String id) async {
    final job = _find(id);
    if (job == null) return;
    _tokens.remove(id)?.cancel();
    _timers.remove(id)?.cancel();
    _set([
      for (final j in _jobs)
        if (j.id != id) j,
    ]);
    await _persist();
    await _store.deleteDir(_dirOf(id));
  }

  /// 멈춘 항목을 [다시 시도] — 멈춘 이유와 실패 횟수를 지우고 처음처럼 다시 태운다.
  Future<void> retry(String id) async {
    if (_find(id)?.stopped != true) return;
    _update(id, (j) => j.copyWith(failures: 0, stoppedCode: () => null));
    await _persist();
    unawaited(_pump());
  }

  /// 기다리는 항목을 지금 다시 해 본다(인터넷이 돌아왔을 때). 멈춘 항목은 건드리지 않는다.
  void retryNow() {
    for (final t in _timers.values) {
      t.cancel();
    }
    _timers.clear();
    unawaited(_pump());
  }

  Future<void> _pump() async {
    if (_pumping) return;
    _pumping = true;
    try {
      while (ref.mounted &&
          ref.read(sessionControllerProvider).value is SignedIn) {
        final next = _jobs
            .where(
              (j) =>
                  j.stage != UploadStage.preparing &&
                  !j.running &&
                  !j.stopped &&
                  !_timers.containsKey(j.id),
            )
            .firstOrNull;
        if (next == null) break;
        await _runOne(next);
      }
    } finally {
      _pumping = false;
    }
  }

  Future<void> _runOne(UploadJob job) async {
    _update(job.id, (j) => j.copyWith(running: true, progress: 0));
    try {
      var mediaId = job.mediaId;
      if (job.stage == UploadStage.prepared) {
        mediaId = await _upload(job);
        if (!_has(job.id)) return;
        _update(
          job.id,
          (j) =>
              j.copyWith(stage: UploadStage.confirmed, mediaId: () => mediaId),
        );
        await _persist();
      }
      await runShopScoped(
        ref,
        () => ref
            .read(visitApiProvider)
            .appendRecordMedia(
              job.shopId,
              job.visitId,
              mediaId: mediaId!,
              phase: job.phase,
            ),
      );
      await _finish(job.id);
    } catch (e) {
      // 뺐거나(올리던 것은 취소 — CANCELLED) 대기열이 사라졌으면 조용히 끝낸다. 실패로 세지 않는다.
      if (!ref.mounted || !_has(job.id)) return;
      if (e is FileSystemException) {
        // 로컬 파일이 사라졌다 — 올릴 수 없으니 뺀다.
        await remove(job.id);
        return;
      }
      if (e is ApiException && e.code == 'MEDIA_NOT_FOUND') {
        // 서버가 붙지 않은 사진을 정리했다 — 간격을 두고 로컬 파일로 발급부터 다시 한다.
        if (_find(job.id)?.mediaId != null) {
          _update(
            job.id,
            (j) => j.copyWith(stage: UploadStage.prepared, mediaId: () => null),
          );
          await _persist();
        }
      } else if (stopsUpload(e)) {
        await _stop(job.id, (e as ApiException).code);
        return;
      }
      _fail(job.id);
    }
  }

  /// 발급 → 올리기 셋(동시에) → 확인. 확인된 미디어 ID 를 돌려준다.
  Future<int> _upload(UploadJob job) async {
    final files = [
      File(job.originalPath!),
      File(job.displayPath!),
      File(job.thumbPath!),
    ];
    final lengths = [for (final f in files) await f.length()];
    final media = ref.read(mediaApiProvider);
    final issued = await runShopScoped(
      ref,
      () => media.issuePhoto(
        job.shopId,
        byteSize: lengths[0],
        width: job.width,
        height: job.height,
      ),
    );
    final urls = [
      issued.puts.original,
      issued.puts.display!,
      issued.puts.thumb,
    ];
    final total = lengths.reduce((a, b) => a + b);
    final sent = List<int>.filled(files.length, 0);
    final token = _tokens[job.id] = CancelToken();
    final client = ref.read(uploadClientProvider);
    try {
      await Future.wait([
        for (var i = 0; i < files.length; i++)
          client.put(
            Uri.parse(urls[i]),
            body: files[i].openRead(),
            length: lengths[i],
            contentType: 'image/jpeg',
            cancelToken: token,
            onSendProgress: (s, _) {
              sent[i] = s;
              _progress(job.id, sent.reduce((a, b) => a + b) / total);
            },
          ),
      ]);
    } finally {
      _tokens.remove(job.id);
    }
    await runShopScoped(ref, () => media.confirm(job.shopId, issued.mediaId));
    return issued.mediaId;
  }

  /// 붙었다 — 대기열에서 빼고 파일을 지우고, 사진이 보이는 화면을 다시 읽게 한다.
  Future<void> _finish(String id) async {
    _set([
      for (final j in _jobs)
        if (j.id != id) j,
    ]);
    await _persist();
    await _store.deleteDir(_dirOf(id));
    ref.invalidate(visitDetailProvider);
    ref.invalidate(dayVisitsProvider);
    ref.invalidate(calendarMonthProvider);
    ref.invalidate(feedControllerProvider);
    ref.invalidate(customerListControllerProvider);
    ref.invalidate(customerDetailProvider);
    // 프로필 사진은 가장 최근 완료 기록의 대표 사진이다.
    ref.invalidate(petDetailProvider);
  }

  /// 다시 해도 안 되는 실패 — 스스로 다시 하지 않고 이유를 남긴다. 파일은 그대로 둔다.
  Future<void> _stop(String id, String code) async {
    _update(
      id,
      (j) => j.copyWith(running: false, progress: 0, stoppedCode: () => code),
    );
    await _persist();
  }

  void _fail(String id) {
    final failures = (_find(id)?.failures ?? 0) + 1;
    _update(
      id,
      (j) => j.copyWith(running: false, failures: failures, progress: 0),
    );
    _timers[id] = ref.read(uploadRetrySchedulerProvider)(
      retryDelay(failures),
      () {
        _timers.remove(id);
        unawaited(_pump());
      },
    );
  }

  void _progress(String id, double value) {
    final rounded = (value * 100).floor() / 100;
    if (_find(id)?.progress == rounded) return;
    _update(id, (j) => j.copyWith(progress: rounded));
  }

  void _onSession(Session? previous, Session? next) {
    if (next is SignedOut && !next.sessionExpired && previous is SignedIn) {
      unawaited(_clear(_jobs));
    } else if (next is SignedIn) {
      final mine = {for (final j in _ownedBy(next.me, _jobs)) j.id};
      final others = [
        for (final j in _jobs)
          if (!mine.contains(j.id)) j,
      ];
      if (others.isNotEmpty) unawaited(_clear(others));
      unawaited(_pump());
    }
  }

  /// [me]의 것이고 아직 멤버인 매장의 항목만.
  List<UploadJob> _ownedBy(Me me, List<UploadJob> jobs) => [
    for (final j in jobs)
      if (j.userId == me.id && me.shops.any((s) => s.shopId == j.shopId)) j,
  ];

  Future<void> _clear(Iterable<UploadJob> jobs) async {
    final ids = {for (final j in jobs) j.id};
    for (final id in ids) {
      _tokens.remove(id)?.cancel();
      _timers.remove(id)?.cancel();
    }
    _set([
      for (final j in _jobs)
        if (!ids.contains(j.id)) j,
    ]);
    await _persist();
    for (final id in ids) {
      await _store.deleteDir(_dirOf(id));
    }
  }

  /// 항목의 폴더. 렌디션을 만드는 중이라 [UploadJob.dir]가 아직 없어도 같은 자리다.
  String _dirOf(String id) => '${_store.root.path}/$id';

  bool _has(String id) => _find(id) != null;

  UploadJob? _find(String id) => _jobs.where((j) => j.id == id).firstOrNull;

  void _set(List<UploadJob> jobs) => state = AsyncData(jobs);

  void _update(String id, UploadJob Function(UploadJob) change) =>
      _set([for (final j in _jobs) j.id == id ? change(j) : j]);

  /// 차례로 쓴다 — 늦게 시작한 쓰기가 먼저 끝나 옛 목록을 남기지 않게.
  Future<void> _persist() =>
      _saving = _saving.then((_) => _store.save(_jobs)).catchError((_) {});
}

final uploadQueueProvider = AsyncNotifierProvider<UploadQueue, List<UploadJob>>(
  UploadQueue.new,
);

/// 한 방문의 대기 중인 사진(넣은 순서).
final visitUploadsProvider = Provider.autoDispose.family<List<UploadJob>, int>(
  (ref, visitId) => [
    for (final j in ref.watch(uploadQueueProvider).value ?? const [])
      if (j.visitId == visitId) j,
  ],
);
