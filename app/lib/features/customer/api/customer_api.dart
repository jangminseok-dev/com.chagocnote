import '../../../core/error/api_exception.dart';
import '../../../core/proxy/api_client.dart';
import '../../../core/time/shop_time.dart';
import 'customer_models.dart';

/// 고객·반려동물 API. 경로는 모두 `/v1/shops/{shopId}` 아래다.
class CustomerApi {
  CustomerApi(this._client);

  final ApiClient _client;

  /// 가족 카드 목록 한 페이지. [q]가 비어 있으면 보내지 않는다.
  Future<CustomerPage> list(
    int shopId, {
    String? q,
    String sort = 'recent',
    bool includePassed = false,
    String? cursor,
  }) async {
    final data =
        await _client.get(
              '/v1/shops/$shopId/customers',
              queryParameters: {
                if (q != null && q.isNotEmpty) 'q': q,
                'sort': sort,
                'include_passed': includePassed,
                'cursor': ?cursor,
              },
            )
            as Map<String, dynamic>;
    return CustomerPage.fromJson(data);
  }

  /// 등록 1단계. 이 번호의 고객이 없으면(404 `CUSTOMER_NOT_FOUND`) null.
  Future<CustomerLookup?> lookup(int shopId, String phoneDigits) async {
    try {
      final data =
          await _client.get(
                '/v1/shops/$shopId/customers/lookup',
                queryParameters: {'phone': phoneDigits},
              )
              as Map<String, dynamic>;
      return CustomerLookup.fromJson(data);
    } on ApiException catch (e) {
      if (e.code == 'CUSTOMER_NOT_FOUND') return null;
      rethrow;
    }
  }

  /// 보호자와 첫 반려동물을 한 번에 등록한다.
  Future<CustomerDetail> register(
    int shopId, {
    required CustomerFields customer,
    required PetFields pet,
  }) async {
    final data =
        await _client.post(
              '/v1/shops/$shopId/customers',
              data: {'customer': customer.toJson(), 'pet': pet.toJson()},
            )
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  Future<CustomerDetail> customer(int shopId, int customerId) async {
    final data =
        await _client.get('/v1/shops/$shopId/customers/$customerId')
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  Future<CustomerDetail> updateCustomer(
    int shopId,
    int customerId,
    CustomerFields fields,
  ) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/customers/$customerId',
              data: fields.toJson(),
            )
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  /// 익명화 삭제(사장만).
  Future<void> deleteCustomer(int shopId, int customerId) async {
    await _client.delete('/v1/shops/$shopId/customers/$customerId');
  }

  Future<PetDetail> addPet(int shopId, int customerId, PetFields fields) async {
    final data =
        await _client.post(
              '/v1/shops/$shopId/customers/$customerId/pets',
              data: fields.toJson(),
            )
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> pet(int shopId, int petId) async {
    final data =
        await _client.get('/v1/shops/$shopId/pets/$petId')
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> updatePet(int shopId, int petId, PetFields fields) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/pets/$petId',
              data: fields.toJson(),
            )
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> markPassedAway(int shopId, int petId) async {
    final data =
        await _client.post('/v1/shops/$shopId/pets/$petId/passed-away')
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> unmarkPassedAway(int shopId, int petId) async {
    final data =
        await _client.delete('/v1/shops/$shopId/pets/$petId/passed-away')
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  /// 잘못 등록한 반려동물 삭제. 마지막 한 마리면 409 `LAST_PET`.
  Future<void> deletePet(int shopId, int petId) async {
    await _client.delete('/v1/shops/$shopId/pets/$petId');
  }

  /// 이 고객 카드가 보호자 계정에 이어져 있는지(여부와 이은 날뿐이다).
  Future<GuardianLink> guardianLink(int shopId, int customerId) async {
    final data =
        await _client.get(
              '/v1/shops/$shopId/customers/$customerId/guardian-link',
            )
            as Map<String, dynamic>;
    return GuardianLink.fromJson(data);
  }

  /// 매장이 보호자 연결을 끊는다. 연결이 없으면 404 `GUARDIAN_LINK_NOT_FOUND`.
  Future<void> endGuardianLink(int shopId, int customerId) async {
    await _client.delete(
      '/v1/shops/$shopId/customers/$customerId/guardian-link',
    );
  }

  /// 미용 동의서를 받았다고 적는다(③-B). [receivedOn]이 없으면 서버가 오늘로 적는다.
  Future<PetDetail> setGroomingConsent(
    int shopId,
    int petId, {
    DateTime? receivedOn,
  }) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/pets/$petId/grooming-consent',
              data: {
                'received_on': receivedOn == null ? null : isoDay(receivedOn),
              },
            )
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  Future<PetDetail> clearGroomingConsent(int shopId, int petId) async {
    final data =
        await _client.delete('/v1/shops/$shopId/pets/$petId/grooming-consent')
            as Map<String, dynamic>;
    return PetDetail.fromJson(data);
  }

  /// 주의 고객으로 표시한다(③-B). 사유는 1~100자 한 줄. 기한은 서버가 정한다.
  Future<CustomerDetail> setCaution(
    int shopId,
    int customerId,
    String reason,
  ) async {
    final data =
        await _client.put(
              '/v1/shops/$shopId/customers/$customerId/caution',
              data: {'reason': reason},
            )
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  /// 주의 표시를 지운다. 없어도 성공한다.
  Future<CustomerDetail> clearCaution(int shopId, int customerId) async {
    final data =
        await _client.delete('/v1/shops/$shopId/customers/$customerId/caution')
            as Map<String, dynamic>;
    return CustomerDetail.fromJson(data);
  }

  /// 정해진 질병 종류(칩 순서대로).
  Future<List<ConditionType>> conditionTypes(int shopId) async {
    final data =
        await _client.get('/v1/shops/$shopId/pet-condition-types') as List;
    return data
        .map((e) => ConditionType.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
