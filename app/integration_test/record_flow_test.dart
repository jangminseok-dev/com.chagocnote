// ④-2a 완료 기준 — 실제 백엔드(MinIO 포함)에 붙은 앱을 시뮬레이터에서 조작해 사진 올리기·기록·완료
// 흐름을 확인한다. 확인·스크린샷 도구는 `flow_kit.dart`.
//
// 사진 선택기만 바꿔 끼운다 — 4000×3000 PNG 두 장을 만들어 준다. 렌디션(압축 플러그인)·발급·올리기·확인·
// 덧붙이기는 실제로 한다.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_record_flow.sh → 마지막 줄의 --dart-define 들(방문 둘을 쓰므로 실행마다 새로)
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/record_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'dart:convert';
import 'dart:io';

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';
import 'gps_photo.dart';

const shopId = int.fromEnvironment('SHOP');
const visitA = int.fromEnvironment('VISIT_A');
const visitB = int.fromEnvironment('VISIT_B');
const ownerName = String.fromEnvironment('OWNER');
const staffName = String.fromEnvironment('STAFF');

/// 앨범 대신 — 4000×3000 PNG 한 장(렌디션이 3000 으로 줄이는지)과 GPS·기기명·방향 6 이 든 JPEG 한 장
/// (EXIF 를 지우고 방향을 픽셀에 적용하는지)을 준다.
class GeneratedPicker implements MediaPicker {
  var made = 0;

  Future<String> _make() => makePhoto('rflow-$made', made++);

  @override
  Future<List<String>> pickPhotos({required int limit}) async {
    final gps = File('${Directory.systemTemp.path}/rflow-gps.jpg');
    await gps.writeAsBytes(base64Decode(gpsPhotoBase64));
    return [await _make(), gps.path];
  }

  @override
  Future<String?> takePhoto() => _make();
}

/// JPEG 의 EXIF(APP1) IFD0 태그 번호들. EXIF 가 없으면 빈 집합.
Set<int> exifTags(List<int> jpeg) {
  var i = 2;
  while (i + 4 < jpeg.length && jpeg[i] == 0xFF) {
    final marker = jpeg[i + 1];
    final length = (jpeg[i + 2] << 8) | jpeg[i + 3];
    if (marker == 0xDA) break;
    final seg = jpeg.sublist(i + 4, i + 2 + length);
    if (marker == 0xE1 &&
        ascii.decode(seg.take(4).toList(), allowInvalid: true) == 'Exif') {
      final tiff = seg.sublist(6);
      final le = tiff[0] == 0x49;
      int u16(int o) =>
          le ? tiff[o] | (tiff[o + 1] << 8) : (tiff[o] << 8) | tiff[o + 1];
      int u32(int o) =>
          le ? u16(o) | (u16(o + 2) << 16) : (u16(o) << 16) | u16(o + 2);
      final ifd = u32(4);
      return {for (var k = 0; k < u16(ifd); k++) u16(ifd + 2 + 12 * k)};
    }
    i += 2 + length;
  }
  return {};
}

bool containsAscii(List<int> bytes, String text) {
  final needle = text.codeUnits;
  for (var i = 0; i + needle.length <= bytes.length; i++) {
    var hit = true;
    for (var j = 0; j < needle.length; j++) {
      if (bytes[i + j] != needle[j]) {
        hit = false;
        break;
      }
    }
    if (hit) return true;
  }
  return false;
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('④-2a 완료 기준', timeout: const Timeout(Duration(minutes: 20)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    await t.pumpWidget(
      buildRoot(
        overrides: [mediaPickerProvider.overrideWithValue(GeneratedPicker())],
      ),
    );
    final end = DateTime.now().add(const Duration(seconds: 40));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 100));
      drain();
      if (find.byKey(ScreenKeys.login).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.home).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.shopSelect).evaluate().isNotEmpty) {
        break;
      }
    }
    if (find.byKey(ScreenKeys.login).evaluate().isEmpty) await logout();
    await login(ownerName);

    await step(
      '1',
      '미용 중 상세 → 사진 추가(전) 두 장 → 올라가 기록에 붙는다, 원본은 3000·JPEG·EXIF 없음',
      () async {
        await openVisit(visitA);
        await shot('01a-detail-in-progress');
        await tap(p(AppStrings.addPhoto));
        await shot('01b-add-sheet');
        await tap(btn(AppStrings.pickFromAlbum));
        await pumpFor(const Duration(milliseconds: 700));
        await shot('01c-uploading');
        await waitFor(p('전 사진 2'), timeout: const Duration(seconds: 90));
        await shot('01d-attached');
        final detail = await container
            .read(visitApiProvider)
            .detail(shopId, visitA);
        final media = detail.record?.media ?? const <RecordMedia>[];
        note(
          '붙은 사진 ${media.length}장 — ${[for (final m in media) '${m.phase.code} ${m.width}×${m.height}']}',
        );
        soft(media.length == 2, '사진이 두 장 붙지 않았다');
        soft(media.every((m) => m.phase == MediaPhase.before), '전 사진이 아니다');
        soft(
          media.length == 2 &&
              media[0].width == 3000 &&
              media[0].height == 2250,
          '4000×3000 이 긴 변 3000 으로 줄지 않았다',
        );
        soft(
          media.length == 2 && media[1].width == 300 && media[1].height == 400,
          '방향 6 사진이 세워지지 않았다(300×400)',
        );
        if (media.length == 2) {
          final original = await download(media[0].originalUrl);
          final thumb = await download(media[0].thumbUrl);
          note('원본 ${original.length}B, 썸네일 ${thumb.length}B');
          soft(
            original.length > 2 && original[0] == 0xFF && original[1] == 0xD8,
            '원본이 JPEG 가 아니다',
          );
          soft(thumb.length < original.length, '썸네일이 원본보다 작지 않다');
          final gps = await download(media[1].originalUrl);
          final tags = exifTags(gps);
          note(
            'GPS 사진의 올라간 원본 EXIF IFD0 태그 = ${[for (final t in tags) '0x${t.toRadixString(16)}']}',
          );
          soft(!tags.contains(0x8825), '올라간 원본에 GPS 가 남았다');
          soft(
            !tags.contains(0x010F) && !tags.contains(0x0110),
            '올라간 원본에 기기명이 남았다',
          );
          soft(!containsAscii(gps, 'TestCam'), '올라간 원본에 기기명 글자가 남았다');
        }
      },
    );

    await step('2', '완료 → 기록 화면 미리 채움(몸무게·정가·총액) → 완료하기 → 다음 예약 시트', () async {
      await openVisit(visitA);
      await tap(btn(AppStrings.actionComplete));
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await pumpFor(const Duration(seconds: 1));
      await shot('02a-record-prefilled');
      final weight = find.widgetWithText(TextField, '3.2');
      soft(weight.evaluate().isNotEmpty, '몸무게가 3.2 로 채워지지 않았다');
      soft(
        fieldText('total') == '30000',
        '총액이 정가 30000 으로 채워지지 않았다(${fieldText('total')})',
      );
      await tap(p(AppStrings.paymentCard));
      await enter('careNote', '발바닥 각질이 있어 보습했어요.');
      await enter('internalNote', '드라이어 소리에 예민');
      await shot('02b-record-filled');
      await tap(btn(AppStrings.completeWithRecord));
      await waitFor(find.text(AppStrings.completeTitle));
      await shot('02c-next-sheet');
      soft(find.textContaining('→ ').evaluate().isNotEmpty, '다음 예약 미리보기가 없다');
      await tap(btn(AppStrings.close));
      await waitFor(find.text('목욕 · 30,000원'));
      await shot('02d-detail-care');
      soft(
        find
            .text(
              '${AppStrings.totalLabel} 30,000원 · ${AppStrings.paymentCard}',
            )
            .evaluate()
            .isNotEmpty,
        '총액·결제 줄이 없다',
      );
      soft(
        find.text(AppStrings.statusCompleted).evaluate().isNotEmpty,
        '완료로 보이지 않는다',
      );
    });

    await step('3', '[기록 수정] → 총액을 고쳐 저장(할인)', () async {
      await openVisit(visitA);
      await tap(btn(AppStrings.editRecord));
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await pumpFor(const Duration(seconds: 1));
      soft(p('전 사진 2').evaluate().isNotEmpty, '기록 화면에 붙은 사진 둘이 없다');
      await enter('total', '27000');
      await tap(btn(AppStrings.save));
      await waitFor(
        find.text(
          '${AppStrings.totalLabel} 27,000원 · ${AppStrings.paymentCard}',
        ),
      );
      await shot('03-detail-discount');
    });

    await step('4', '되돌려도 기록은 남는다', () async {
      await openVisit(visitA);
      await tap(p(AppStrings.more));
      await tap(find.text(AppStrings.actionRevert));
      await waitFor(find.text(AppStrings.statusReserved));
      await pumpFor(const Duration(seconds: 1));
      await shot('04-reverted');
      soft(
        find.text('목욕 · 30,000원').evaluate().isNotEmpty,
        '되돌린 뒤 기록이 보이지 않는다',
      );
    });

    await step('5', '직원 — 나중에 적고 완료 → [기록 쓰기]로 돈 칸까지 저장', () async {
      await logout();
      await login(staffName);
      await openVisit(visitB);
      await tap(btn(AppStrings.actionComplete));
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await tap(btn(AppStrings.completeWithoutRecord));
      await waitFor(find.text(AppStrings.completeTitle));
      await tap(btn(AppStrings.close));
      await waitFor(btn(AppStrings.writeRecord));
      await shot('05a-completed-without-record');
      await tap(btn(AppStrings.writeRecord));
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await pumpFor(const Duration(seconds: 1));
      soft(fieldText('total') == '30000', '직원 화면에 총액이 채워지지 않았다');
      await tap(p(AppStrings.paymentCash));
      await shot('05b-staff-record');
      await tap(btn(AppStrings.save));
      await waitFor(
        find.text(
          '${AppStrings.totalLabel} 30,000원 · ${AppStrings.paymentCash}',
        ),
      );
      await shot('05c-staff-saved');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
