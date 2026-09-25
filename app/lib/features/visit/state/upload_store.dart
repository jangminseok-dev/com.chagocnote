import 'dart:convert';
import 'dart:io';

import 'upload_job.dart';

/// 대기열을 앱 폴더의 `queue.json`에 남긴다. 렌디션을 다 만든 항목만 남긴다
/// ([UploadStage.preparing]은 뺀다).
class UploadStore {
  UploadStore(this.root);

  /// 업로드 폴더. 항목마다 하위 폴더가 있고 `queue.json`이 목록이다.
  final Directory root;

  File get _file => File('${root.path}/queue.json');

  Future<List<UploadJob>> load() async {
    final file = _file;
    if (!await file.exists()) return [];
    try {
      final list = jsonDecode(await file.readAsString()) as List;
      return [
        for (final e in list)
          UploadJob.fromJson(e as Map<String, dynamic>, root.path),
      ];
    } on FormatException {
      // 쓰다가 꺼져 깨진 파일이면 버린다. 폴더의 사진은 [deleteOrphans]가 치운다.
      return [];
    }
  }

  /// 새 파일에 쓰고 이름을 바꾼다 — 쓰다가 꺼져도 이전 목록이 남는다.
  Future<void> save(List<UploadJob> jobs) async {
    final kept = [
      for (final j in jobs)
        if (j.stage != UploadStage.preparing) j.toJson(),
    ];
    final temp = File('${root.path}/queue.json.tmp');
    await temp.writeAsString(jsonEncode(kept), flush: true);
    await temp.rename(_file.path);
  }

  /// 목록에 없는 항목 폴더를 지운다(렌디션을 만들다 꺼진 것 등).
  Future<void> deleteOrphans(Iterable<UploadJob> jobs) async {
    final keep = {for (final j in jobs) j.dir};
    await for (final entry in root.list()) {
      if (entry is Directory && !keep.contains(entry.path)) {
        await entry.delete(recursive: true);
      }
    }
  }

  Future<void> deleteDir(String? dir) async {
    if (dir == null) return;
    final d = Directory(dir);
    if (await d.exists()) await d.delete(recursive: true);
  }
}
