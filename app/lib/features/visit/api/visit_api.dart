import '../../../core/proxy/api_client.dart';
import 'record_models.dart';
import 'visit_models.dart';

/// 예약·방문·매장 일정·메뉴표 API. 경로는 모두 `/v1/shops/{shopId}` 아래다.
class VisitApi {
  VisitApi(this._client);

  final ApiClient _client;

  Future<Map<String, dynamic>> _get(
    String path, [
    Map<String, dynamic>? query,
  ]) async =>
      await _client.get(path, queryParameters: query) as Map<String, dynamic>;

  /// 하루 목록(취소·노쇼 포함).
  Future<DayVisits> day(int shopId, DateTime date) async => DayVisits.fromJson(
    await _get('/v1/shops/$shopId/visits', {'date': isoDay(date)}),
  );

  /// 월 요약. [month]는 그달의 아무 날.
  Future<CalendarMonth> calendar(int shopId, DateTime month) async =>
      CalendarMonth.fromJson(
        await _get('/v1/shops/$shopId/visits/calendar', {
          'month': isoMonth(month),
        }),
      );

  /// 시간 칸의 경고. [at](`HH:MM`)을 주면 그 한 시각만, 없으면 영업시간 안의
  /// 정시 칸 전부. [exclude]는 옮길 방문(자기 자신과 겹치지 않게).
  Future<VisitSlots> slots(
    int shopId, {
    required DateTime date,
    required int durationMinutes,
    String? at,
    List<int> exclude = const [],
  }) async => VisitSlots.fromJson(
    await _get('/v1/shops/$shopId/visits/slots', {
      'date': isoDay(date),
      'duration': durationMinutes,
      'at': ?at,
      if (exclude.isNotEmpty) 'exclude': exclude,
    }),
  );

  Future<VisitDefaults> defaults(int shopId, int petId) async =>
      VisitDefaults.fromJson(
        await _get('/v1/shops/$shopId/visits/defaults', {'pet_id': petId}),
      );

  Future<SavedVisits> register(int shopId, VisitRequest request) async =>
      SavedVisits.fromJson(
        await _client.post('/v1/shops/$shopId/visits', data: request.toJson())
            as Map<String, dynamic>,
      );

  Future<VisitDetail> detail(int shopId, int visitId) async =>
      VisitDetail.fromJson(await _get('/v1/shops/$shopId/visits/$visitId'));

  /// 기록 전체 교체(설계 8절). 버전이 다르면 409 `RECORD_VERSION_CONFLICT`.
  Future<VisitRecord> putRecord(
    int shopId,
    int visitId,
    RecordInput input,
  ) async => VisitRecord.fromJson(
    await _client.put(
          '/v1/shops/$shopId/visits/$visitId/record',
          data: input.toJson(),
        )
        as Map<String, dynamic>,
  );

  /// 사진 하나를 그 칸 맨 뒤에 붙인다. 같은 사진을 다시 보내도 한 번만 붙는다.
  Future<VisitRecord> appendRecordMedia(
    int shopId,
    int visitId, {
    required int mediaId,
    required MediaPhase phase,
  }) async => VisitRecord.fromJson(
    await _client.post(
          '/v1/shops/$shopId/visits/$visitId/record/media',
          data: {'media_id': mediaId, 'phase': phase.code},
        )
        as Map<String, dynamic>,
  );

  Future<void> deleteRecord(int shopId, int visitId) async {
    await _client.delete('/v1/shops/$shopId/visits/$visitId/record');
  }

  /// 방문 하나 수정. 응답은 `{visit, warnings}` — 방문 하나를 [SavedVisits]로 감싼다.
  Future<SavedVisits> update(
    int shopId,
    int visitId,
    VisitUpdate update,
  ) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/visits/$visitId',
              data: update.toJson(),
            )
            as Map<String, dynamic>;
    return SavedVisits(
      visits: [Visit.fromJson(data['visit'] as Map<String, dynamic>)],
      warnings: (data['warnings'] as List).cast<String>(),
    );
  }

  /// 묶음 한 번에 상태 전이. [cancelReason]은 취소일 때만.
  Future<List<Visit>> transition(
    int shopId, {
    required List<int> visitIds,
    required VisitAction action,
    String? cancelReason,
  }) async {
    final data =
        await _client.post(
              '/v1/shops/$shopId/visits/transitions',
              data: {
                'visit_ids': visitIds,
                'action': action.code,
                'cancel_reason': ?cancelReason,
              },
            )
            as Map<String, dynamic>;
    return (data['visits'] as List)
        .map((e) => Visit.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 묶음 한 번에 옮기기. [startsAt]은 서버가 준 시각 문자열 그대로.
  Future<SavedVisits> reschedule(
    int shopId, {
    required List<int> visitIds,
    required String startsAt,
  }) async => SavedVisits.fromJson(
    await _client.post(
          '/v1/shops/$shopId/visits/reschedule',
          data: {'visit_ids': visitIds, 'starts_at': startsAt},
        )
        as Map<String, dynamic>,
  );

  /// 완료한 방문의 다음 예약 초안(저장하지 않는다).
  Future<NextVisitDraft> nextDraft(int shopId, int visitId) async =>
      NextVisitDraft.fromJson(
        await _get('/v1/shops/$shopId/visits/$visitId/next-draft'),
      );

  /// 카톡 글 → 예약 초안(③-A3). 서버는 글을 저장하지 않는다.
  Future<VisitDraft> parseDraft(int shopId, String text) async =>
      VisitDraft.fromJson(
        await _client.post(
              '/v1/shops/$shopId/visit-drafts',
              data: {'text': text},
            )
            as Map<String, dynamic>,
      );

  Future<VisitSettings> settings(int shopId) async =>
      VisitSettings.fromJson(await _get('/v1/shops/$shopId/visit-settings'));

  Future<VisitSettings> updateSettings(
    int shopId,
    VisitSettings settings,
  ) async => VisitSettings.fromJson(
    await _client.put(
          '/v1/shops/$shopId/visit-settings',
          data: settings.toJson(),
        )
        as Map<String, dynamic>,
  );

  Future<List<ClosedDate>> closedDates(
    int shopId, {
    required DateTime from,
    required DateTime to,
  }) async {
    final data = await _get('/v1/shops/$shopId/closed-dates', {
      'from': isoDay(from),
      'to': isoDay(to),
    });
    return (data['items'] as List)
        .map((e) => ClosedDate.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 임시 휴무 추가. 이미 있으면 서버가 그대로 200 을 준다.
  Future<ClosedDate> addClosedDate(
    int shopId,
    DateTime date, {
    String? note,
  }) async => ClosedDate.fromJson(
    await _client.post(
          '/v1/shops/$shopId/closed-dates',
          data: {'date': isoDay(date), 'note': note},
        )
        as Map<String, dynamic>,
  );

  Future<void> deleteClosedDate(int shopId, DateTime date) async {
    await _client.delete('/v1/shops/$shopId/closed-dates/${isoDay(date)}');
  }

  Future<List<Menu>> menus(int shopId, {bool includeArchived = false}) async {
    final data = await _get('/v1/shops/$shopId/menus', {
      'include_archived': includeArchived,
    });
    return (data['items'] as List)
        .map((e) => Menu.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Menu> createMenu(
    int shopId, {
    required String name,
    int? defaultDurationMinutes,
    int? price,
  }) async => Menu.fromJson(
    await _client.post(
          '/v1/shops/$shopId/menus',
          data: {
            'name': name,
            'default_duration_minutes': defaultDurationMinutes,
            'price': price,
          },
        )
        as Map<String, dynamic>,
  );

  Future<Menu> updateMenu(
    int shopId,
    int menuId, {
    required String name,
    required int? defaultDurationMinutes,
    required int sortOrder,
    required int? price,
  }) async => Menu.fromJson(
    // 전체 교체다 — 정가를 빼면 서버가 가격 미정으로 바꾼다. 순서만 바꿀 때도 정가를 그대로 보낸다.
    await _client.put(
          '/v1/shops/$shopId/menus/$menuId',
          data: {
            'name': name,
            'default_duration_minutes': defaultDurationMinutes,
            'sort_order': sortOrder,
            'price': price,
          },
        )
        as Map<String, dynamic>,
  );

  Future<Menu> archiveMenu(int shopId, int menuId) async => Menu.fromJson(
    await _client.post('/v1/shops/$shopId/menus/$menuId/archive')
        as Map<String, dynamic>,
  );
}
