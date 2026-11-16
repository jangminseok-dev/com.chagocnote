import 'dart:typed_data';
import 'dart:ui' as ui;

/// 서명 그림의 크기(⑪ 설계 3.3) — 백엔드의 상한과 같다. 화면 배율을 곱하지 않는다.
const signatureWidth = 600;
const signatureHeight = 240;
const signatureMaxBytes = 65536;

/// 서명의 선들을 PNG 로 만든다. [strokes] 의 점은 칸의 폭·높이에 대한 비율(0~1)이다.
///
/// 흰 바탕에 검은 선이다 — 어두운 화면에서 보아도 선이 보인다. 600×240 으로 만들고,
/// 65,536바이트를 넘으면 300×120 으로 다시 만든다(그래도 넘으면 그것을 돌려준다 — 서버가 거절한다).
Future<Uint8List> signaturePng(List<List<ui.Offset>> strokes, {int maxBytes = signatureMaxBytes}) async {
  final full = await _render(strokes, signatureWidth, signatureHeight);
  if (full.length <= maxBytes) return full;
  return _render(strokes, signatureWidth ~/ 2, signatureHeight ~/ 2);
}

Future<Uint8List> _render(List<List<ui.Offset>> strokes, int width, int height) async {
  final recorder = ui.PictureRecorder();
  final canvas = ui.Canvas(recorder);
  paintSignature(canvas, ui.Size(width.toDouble(), height.toDouble()), strokes, background: true);
  final picture = recorder.endRecording();
  final image = await picture.toImage(width, height);
  try {
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    return data!.buffer.asUint8List();
  } finally {
    image.dispose();
    picture.dispose();
  }
}

/// 선들을 [size] 의 칸에 그린다. 화면의 서명 칸과 PNG 가 같은 그림을 쓴다.
void paintSignature(ui.Canvas canvas, ui.Size size, List<List<ui.Offset>> strokes, {bool background = false}) {
  if (background) {
    canvas.drawRect(ui.Offset.zero & size, ui.Paint()..color = const ui.Color(0xFFFFFFFF));
  }
  // 굵기는 600 폭에서 3 이다 — 칸이 작아도 같은 비율로 보인다.
  final width = size.width * 3 / signatureWidth;
  final line = ui.Paint()
    ..color = const ui.Color(0xFF161616)
    ..style = ui.PaintingStyle.stroke
    ..strokeWidth = width
    ..strokeCap = ui.StrokeCap.round
    ..strokeJoin = ui.StrokeJoin.round;
  final dot = ui.Paint()..color = const ui.Color(0xFF161616);
  for (final stroke in strokes) {
    if (stroke.isEmpty) continue;
    ui.Offset at(ui.Offset p) => ui.Offset(p.dx * size.width, p.dy * size.height);
    if (stroke.length == 1) {
      // 점만 찍고 뗀 것도 남긴다.
      canvas.drawCircle(at(stroke.first), width / 2, dot);
      continue;
    }
    final path = ui.Path()..moveTo(at(stroke.first).dx, at(stroke.first).dy);
    for (final point in stroke.skip(1)) {
      path.lineTo(at(point).dx, at(point).dy);
    }
    canvas.drawPath(path, line);
  }
}
