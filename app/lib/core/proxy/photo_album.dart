import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gal/gal.dart';

/// 사진 보관함(앨범)에 저장하기 — 화면이 `gal`을 직접 부르지 않게 감싼 자리. 원본 저장(설계 10.1 ⑤)에 쓴다.
abstract class PhotoAlbum {
  /// 기기의 사진 파일 하나를 앨범에 넣는다. 사용자가 권한을 주지 않으면 [PhotoAlbumDenied].
  Future<void> save(String path);
}

/// 앨범 권한이 없다 — 설정에서 켜야 한다.
class PhotoAlbumDenied implements Exception {
  const PhotoAlbumDenied();
}

class GalPhotoAlbum implements PhotoAlbum {
  // 앨범에 넣기만 하므로 추가 권한만 묻는다(iOS 는 NSPhotoLibraryAddUsageDescription).
  @override
  Future<void> save(String path) async {
    if (!await Gal.hasAccess() && !await Gal.requestAccess()) {
      throw const PhotoAlbumDenied();
    }
    try {
      await Gal.putImage(path);
    } on GalException catch (e) {
      if (e.type == GalExceptionType.accessDenied) {
        throw const PhotoAlbumDenied();
      }
      rethrow;
    }
  }
}

final photoAlbumProvider = Provider<PhotoAlbum>((ref) => GalPhotoAlbum());
