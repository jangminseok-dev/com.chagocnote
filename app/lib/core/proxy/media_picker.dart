import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

/// 사진·영상 고르기·찍기 — 화면이 `image_picker`를 직접 부르지 않게 감싼 자리.
///
/// 돌려주는 것은 플러그인이 만든 임시 파일 경로다. 오래 두지 않는다 — 대기열이 곧바로
/// 렌디션을 만들어 앱 전용 폴더로 옮긴다.
abstract class MediaPicker {
  /// 앨범에서 여러 장. 고르지 않고 닫으면 빈 목록.
  Future<List<String>> pickPhotos({required int limit});

  /// 카메라로 한 장. 찍지 않고 닫으면 null.
  Future<String?> takePhoto();

  /// 앨범에서 영상 한 편. 고르지 않고 닫으면 null.
  Future<String?> pickVideo();

  /// 카메라로 [maxSeconds]까지 찍는다. 찍지 않고 닫으면 null.
  Future<String?> takeVideo({required int maxSeconds});
}

class ImagePickerMediaPicker implements MediaPicker {
  ImagePickerMediaPicker([ImagePicker? picker])
    : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  // requestFullMetadata: false — 위치 같은 메타데이터를 달라고 하지 않는다(어차피 렌디션에서 지운다).
  @override
  Future<List<String>> pickPhotos({required int limit}) async {
    final files = await _picker.pickMultiImage(
      limit: limit,
      requestFullMetadata: false,
    );
    return [for (final f in files) f.path];
  }

  @override
  Future<String?> takePhoto() async {
    final file = await _picker.pickImage(
      source: ImageSource.camera,
      requestFullMetadata: false,
    );
    return file?.path;
  }

  // 영상도 플러그인이 만든 임시 파일 경로다(앨범 원본이 아니다) — 대기열이 곧바로 압축한다.
  @override
  Future<String?> pickVideo() async {
    final file = await _picker.pickVideo(source: ImageSource.gallery);
    return file?.path;
  }

  @override
  Future<String?> takeVideo({required int maxSeconds}) async {
    final file = await _picker.pickVideo(
      source: ImageSource.camera,
      maxDuration: Duration(seconds: maxSeconds),
    );
    return file?.path;
  }
}

final mediaPickerProvider = Provider<MediaPicker>(
  (ref) => ImagePickerMediaPicker(),
);
