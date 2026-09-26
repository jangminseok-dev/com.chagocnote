import 'package:chagocnote/core/proxy/photo_album.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('.mp4 는 putVideo, 그 밖은 putImage', () async {
    const channel = MethodChannel('gal');
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          calls.add(call);
          if (call.method == 'hasAccess' || call.method == 'requestAccess') {
            return true;
          }
          return null;
        });
    addTearDown(
      () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null),
    );

    final album = GalPhotoAlbum();
    await album.save('/tmp/video-1.mp4');
    await album.save('/tmp/1.jpg');

    final puts = [
      for (final c in calls)
        if (c.method.startsWith('put'))
          (c.method, (c.arguments as Map)['path']),
    ];
    expect(puts, [
      ('putVideo', '/tmp/video-1.mp4'),
      ('putImage', '/tmp/1.jpg'),
    ]);
  });
}
