import '../../../core/proxy/api_client.dart';
import 'check_models.dart';
import 'feed_models.dart';
import 'record_models.dart';
import 'revisit_models.dart';
import 'visit_models.dart';
import 'wrap_up_models.dart';

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

  /// 완료 방문을 최신순으로 한 쪽씩(설계 9절). [petId]를 주면 그 아이만.
  Future<VisitFeed> feed(int shopId, {String? cursor, int? petId}) async =>
      VisitFeed.fromJson(
        await _get('/v1/shops/$shopId/visits/feed', {
          'cursor': ?cursor,
          'pet_id': ?petId,
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

  /// 예약을 잡기 전의 확인할 것(③-B). [petIds]가 비면 보호자 항목만 온다.
  Future<VisitChecksPreview> checks(
    int shopId, {
    required int customerId,
    required List<int> petIds,
    required DateTime date,
  }) async => VisitChecksPreview.fromJson(
    await _get('/v1/shops/$shopId/visit-checks', {
      'customer_id': customerId,
      if (petIds.isNotEmpty) 'pet_ids': petIds,
      'date': isoDay(date),
    }),
  );

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
  /// 그 예약에 보호자에게 보낼 글의 토막들(⑪-B) — 예약 안내와, 필요하면 동의서 링크. 링크가 없으면 이때
  /// 만들어진다(다시 불러도 같은 링크). 예약 상태가 아니면 빈 목록이다. 모르는 kind 도 글 그대로 싣는다.
  Future<SendBundle> sendBundle(int shopId, int visitId) async => SendBundle.fromJson(
    await _client.post('/v1/shops/$shopId/visits/$visitId/send-bundle') as Map<String, dynamic>,
  );

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

  /// 다시 올 때가 된 아이 한 쪽(⑬, 20개). 지남은 오래 지난 순, 곧은 가까운 순.
  Future<RevisitPage> revisits(
    int shopId,
    RevisitBucket bucket, {
    String? cursor,
  }) async => RevisitPage.fromJson(
    await _get('/v1/shops/$shopId/revisits', {
      'bucket': bucket.code,
      'cursor': ?cursor,
    }),
  );

  /// 곧·지남의 수(⑬). 캘린더 탭이 달력과 따로 읽는다.
  Future<RevisitCounts> revisitCounts(int shopId) async =>
      RevisitCounts.fromJson(await _get('/v1/shops/$shopId/revisits/counts'));

  /// 하루 마무리의 장(⑬). 앞날은 빈 목록이다.
  Future<DayWrapUp> dayWrapUp(int shopId, DateTime day) async => DayWrapUp.fromJson(
    await _get('/v1/shops/$shopId/days/${isoDay(day)}/wrap-up'),
  );

  /// 알림장을 보내지 않음으로 넘긴다(⑬ — 완료이고 기록이 있는 방문만, 아니면 409).
  Future<void> skipReport(int shopId, int visitId) async {
    await _client.put('/v1/shops/$shopId/visits/$visitId/report-skip');
  }

  /// 넘긴 것을 되돌린다(방문 상세).
  Future<void> unskipReport(int shopId, int visitId) async {
    await _client.delete('/v1/shops/$shopId/visits/$visitId/report-skip');
  }

  Future<RevisitSettings> revisitSettings(int shopId) async =>
      RevisitSettings.fromJson(await _get('/v1/shops/$shopId/revisit-settings'));

  /// 매장의 다시 올 때 설정 — 보낸 칸만 바뀐다(빠진 칸은 서버가 지금 값으로 둔다).
  /// `revisit_message: null` 은 처음 글로 돌아가기다.
  Future<RevisitSettings> updateRevisitSettings(
    int shopId,
    Map<String, Object?> changes,
  ) async => RevisitSettings.fromJson(
    await _client.put('/v1/shops/$shopId/revisit-settings', data: changes)
        as Map<String, dynamic>,
  );
}
