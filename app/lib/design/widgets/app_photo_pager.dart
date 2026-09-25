import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_shadows.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 넘기기의 사진 한 장.
class AppPagerPhoto {
  const AppPagerPhoto({
    required this.image,
    required this.label,
    required this.semanticLabel,
    this.video = false,
  });

  final ImageProvider image;

  /// 왼쪽 위 알약 글자(전/후).
  final String label;

  /// 스크린리더가 읽는 이름 — 전/후와 몇째 사진인지 담는다(알약은 따로 읽지 않는다).
  final String semanticLabel;

  /// 영상이면 가운데에 재생 표시를 얹는다.
  final bool video;
}

/// 기울어진 사진 넘기기(기준 목업) — 가운데 사진이 크고, 양옆 사진은 작게 기울어 살짝 보인다.
/// 아래에 `01 / 04`와 점. 가운데 사진을 누르면 [onTap], 옆 사진을 누르면 그 사진으로 넘어간다.
///
/// 사진이 없으면 회색 자리 하나만 보인다. [overlay]는 가운데 사진 아래쪽에 겹쳐 얹는다(글래스 이름 카드).
class AppPhotoPager extends StatefulWidget {
  const AppPhotoPager({
    super.key,
    required this.photos,
    this.onTap,
    this.overlay,
  });

  final List<AppPagerPhoto> photos;
  final ValueChanged<int>? onTap;
  final Widget? overlay;

  static const cardWidth = 162.0;
  static const cardHeight = 176.0;
  static const _height = 206.0;

  @override
  State<AppPhotoPager> createState() => _AppPhotoPagerState();
}

class _AppPhotoPagerState extends State<AppPhotoPager> {
  // 가운데 카드(162)가 화면 폭의 반쯤이라 양옆 카드가 보인다.
  final _controller = PageController(viewportFraction: 0.46);
  int _index = 0;

  @override
  void didUpdateWidget(AppPhotoPager old) {
    super.didUpdateWidget(old);
    // 사진이 빠져 지금 자리가 없어지면 마지막 사진으로.
    if (_index >= widget.photos.length && widget.photos.isNotEmpty) {
      _index = widget.photos.length - 1;
      _controller.jumpToPage(_index);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _tap(int i) {
    if (i == _index) {
      widget.onTap?.call(i);
      return;
    }
    _controller.animateToPage(
      i,
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    final photos = widget.photos;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          height: AppPhotoPager._height,
          child: Stack(
            children: [
              if (photos.isEmpty)
                const Align(
                  alignment: Alignment.topCenter,
                  child: _Card(photo: null),
                )
              else
                PageView.builder(
                  controller: _controller,
                  itemCount: photos.length,
                  onPageChanged: (i) => setState(() => _index = i),
                  itemBuilder: (context, i) => AnimatedBuilder(
                    animation: _controller,
                    builder: (context, child) {
                      final page =
                          _controller.hasClients &&
                              _controller.position.haveDimensions
                          ? _controller.page!
                          : _index.toDouble();
                      final delta = (i - page).clamp(-1.0, 1.0);
                      return Transform.translate(
                        offset: Offset(0, 22 * delta.abs()),
                        child: Transform.rotate(
                          angle: delta * 6 * math.pi / 180,
                          child: Transform.scale(
                            scale: 1 - 0.3 * delta.abs(),
                            alignment: Alignment.topCenter,
                            child: child,
                          ),
                        ),
                      );
                    },
                    child: Align(
                      alignment: Alignment.topCenter,
                      child: Pressable(
                        semanticLabel: photos[i].semanticLabel,
                        onTap: () => _tap(i),
                        child: _Card(photo: photos[i]),
                      ),
                    ),
                  ),
                ),
              if (widget.overlay != null)
                Positioned(
                  left: 0,
                  right: 0,
                  top: 130,
                  child: Center(child: widget.overlay),
                ),
            ],
          ),
        ),
        if (photos.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            '${_two(_index + 1)} / ${_two(photos.length)}',
            style: AppTypography.titleEn.copyWith(fontSize: 12),
          ),
          const SizedBox(height: AppSpacing.xs),
          ExcludeSemantics(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (var i = 0; i < photos.length; i++)
                  Container(
                    width: 5,
                    height: 5,
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: i == _index ? AppColors.ink : AppColors.line,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

String _two(int n) => n.toString().padLeft(2, '0');

class _Card extends StatelessWidget {
  const _Card({required this.photo});

  final AppPagerPhoto? photo;

  @override
  Widget build(BuildContext context) {
    final p = photo;
    return Container(
      width: AppPhotoPager.cardWidth,
      height: AppPhotoPager.cardHeight,
      decoration: BoxDecoration(
        color: p == null ? AppColors.line : null,
        image: p == null
            ? null
            : DecorationImage(image: p.image, fit: BoxFit.cover),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.white, width: 2),
        boxShadow: AppShadows.floating,
      ),
      // 알약·재생 표시는 [AppPagerPhoto.semanticLabel]이 이미 말하므로 읽지 않는다.
      child: p == null
          ? null
          : ExcludeSemantics(
              child: Stack(
                children: [
                  Positioned(left: 8, top: 8, child: _Pill(p.label)),
                  if (p.video)
                    const Center(
                      child: Icon(
                        Icons.play_circle_fill,
                        size: 40,
                        color: AppColors.white,
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
    decoration: BoxDecoration(
      color: AppColors.white,
      borderRadius: BorderRadius.circular(AppRadius.pill),
    ),
    child: Text(text, style: AppTypography.caption.copyWith(fontSize: 10)),
  );
}
