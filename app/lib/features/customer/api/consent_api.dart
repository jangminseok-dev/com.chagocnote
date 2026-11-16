import 'dart:convert';
import 'dart:typed_data';

import '../../../core/proxy/api_client.dart';
import '../../../core/time/shop_time.dart';
import 'consent_models.dart';

/// 전자 동의서 API(⑪-A). 경로는 모두 `/v1/shops/{shopId}` 아래다.
///
/// [forDate] 는 예약 날이다 — 그날에 유효한 동의를 지금 받는다(그날 기한이 지나는지, 그날 노령인지로 문서를 조립한다).
/// 문서를 읽을 때 준 날과 서명을 낼 때 주는 날이 같아야 지문이 맞는다.
class ConsentApi {
  ConsentApi(this._client);

  final ApiClient _client;

  /// 동의서 링크를 만든다. 그 아이들을 모두 담은 살아 있는 링크가 있으면 같은 것이 온다.
  /// 더 받을 것이 없으면 409 `CONSENT_UP_TO_DATE`.
  Future<FormLink> issue(int shopId, List<int> petIds, {DateTime? forDate}) async {
    final data =
        await _client.post(
              '/v1/shops/$shopId/consent-forms',
              data: {'pet_ids': petIds, if (forDate != null) 'for_date': isoDay(forDate)},
            )
            as Map<String, dynamic>;
    return FormLink.fromJson(data);
  }

  /// 보낸 서류 — 살아 있는 링크, 보낸 날 내림차순.
  Future<List<SentForm>> forms(int shopId) async {
    final data = await _client.get('/v1/shops/$shopId/forms') as Map<String, dynamic>;
    return SentForm.listFrom(data['items'] as List);
  }

  /// 링크를 끊는다. 이미 닫힌 링크도 조용히 끝난다.
  Future<void> revoke(int shopId, int formId) async {
    await _client.delete('/v1/shops/$shopId/forms/$formId');
  }

  /// 매장에서 바로 서명받을 문서. 더 받을 것이 없으면 409 `CONSENT_UP_TO_DATE`.
  Future<ConsentDocument> document(int shopId, List<int> petIds, {DateTime? forDate}) async {
    final data =
        await _client.get(
              '/v1/shops/$shopId/consent-document',
              queryParameters: {
                'pet_ids': [...petIds]..sort(),
                if (forDate != null) 'for_date': isoDay(forDate),
              },
            )
            as Map<String, dynamic>;
    return ConsentDocument.fromJson(data);
  }

  /// 현장 서명을 보낸다. 읽은 뒤 내용이 바뀌었으면 409 `CONSENT_DOCUMENT_CHANGED`.
  Future<int> signInShop(
    int shopId, {
    required List<int> petIds,
    required String digest,
    required String signerName,
    required Uint8List png,
    DateTime? forDate,
  }) async {
    final data =
        await _client.post(
              '/v1/shops/$shopId/consent-signatures',
              data: {
                'pet_ids': petIds,
                'doc_digest': digest,
                'signer_name': signerName,
                'signature_png': base64Encode(png),
                if (forDate != null) 'for_date': isoDay(forDate),
              },
            )
            as Map<String, dynamic>;
    return data['signature_id'] as int;
  }

  /// 그 아이의 서명들, 새것부터.
  Future<List<SignatureBrief>> signatures(int shopId, int petId) async {
    final data = await _client.get('/v1/shops/$shopId/pets/$petId/consent-signatures') as Map<String, dynamic>;
    return [for (final item in data['items'] as List) ?SignatureBrief.tryParse(item)];
  }

  Future<SignatureDetail> signature(int shopId, int signatureId) async {
    final data = await _client.get('/v1/shops/$shopId/consent-signatures/$signatureId') as Map<String, dynamic>;
    return SignatureDetail.fromJson(data);
  }

  /// 서명 그림(PNG). 받은 바이트 그대로다.
  Future<Uint8List> signatureImage(int shopId, int signatureId) =>
      _client.getBytes('/v1/shops/$shopId/consent-signatures/$signatureId/image');
}
