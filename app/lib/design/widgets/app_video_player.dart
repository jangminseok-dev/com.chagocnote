import 'dart:async';

import 'package:flutter/material.dart';

import '../../l10n/app_strings.dart';
import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'app_button.dart';
import 'app_video_badge.dart';
import 'pressable.dart';
import 'video_playback.dart';

/// 크게 보기의 영상 페이지 — 포스터 위 재생 버튼, 누르면 [playback] 이 [url] 을 열고 그 자리에서
/// 재생한다(④-3a 설계 5.1). 조작은 직접 그린다: 가운데 재생/일시정지(재생 중엔 2초 뒤 숨김),
/// 아래 얇은 진행 막대(누르거나 끌어 옮김), 오른쪽 남은 시간. 끝나면 처음 자리의 재생 버튼.
///
/// 실패하면 포스터 위에 [errorMessage] 문구와 [다시 시도]. [onRetry] 는 새 URL 을 돌려준다(서명 URL
/// 만료 — 부모가 상세를 다시 읽는다). null 이면 그대로 둔다. 두 손가락 확대는 없다.
/// [playback] 은 부모가 만들고 dispose 한다.
class AppVideoPlayer extends StatefulWidget {
  const AppVideoPlayer({
    super.key,
    required this.playback,
    required this.url,
    required this.poster,
    required this.errorMessage,
    required this.onRetry,
  });

  final VideoPlayback playback;
  final String url;
  final ImageProvider poster;
  final String Function(Object error) errorMessage;
  final Future<String?> Function() onRetry;

  @override
  State<AppVideoPlayer> createState() => _AppVideoPlayerState();
}

class _AppVideoPlayerState extends State<AppVideoPlayer> {
  /// 재생 버튼을 한 번이라도 눌렀다 — 그 전에는 포스터만.
  bool _started = false;

  /// 여는 중(처음 열기·다시 시도).
  bool _opening = false;
  bool _controlsVisible = true;
  Timer? _hide;

  @override
  void dispose() {
    _hide?.cancel();
    super.dispose();
  }

  Future<void> _open(String url) async {
    setState(() {
      _started = true;
      _opening = true;
    });
    await widget.playback.open(url);
    if (!mounted) return;
    setState(() => _opening = false);
    if (widget.playback.state.error == null) await _play();
  }

  Future<void> _retry() async {
    setState(() => _opening = true);
    final url = await widget.onRetry();
    if (!mounted) return;
    if (url == null) {
      setState(() => _opening = false);
      return;
    }
    await _open(url);
  }

  Future<void> _play() async {
    await widget.playback.play();
    _showControls();
  }

  Future<void> _pause() async {
    _hide?.cancel();
    await widget.playback.pause();
    if (mounted) setState(() => _controlsVisible = true);
  }

  /// 조작을 보이고, 재생 중이면 2초 뒤 숨긴다.
  void _showControls() {
    _hide?.cancel();
    if (!mounted) return;
    setState(() => _controlsVisible = true);
    _hide = Timer(const Duration(seconds: 2), () {
      if (mounted && widget.playback.state.playing) {
        setState(() => _controlsVisible = false);
      }
    });
  }

  void _seekAt(double dx, double width, Duration duration) {
    final fraction = (dx / width).clamp(0.0, 1.0);
    widget.playback.seekTo(duration * fraction);
    if (widget.playback.state.playing) _showControls();
  }

  @override
  Widget build(BuildContext context) {
    final poster = Image(image: widget.poster, fit: BoxFit.contain);
    if (!_started) {
      return Stack(
        alignment: Alignment.center,
        children: [
          poster,
          _CenterButton(
            playing: false,
            onTap: () => _open(widget.url),
          ),
        ],
      );
    }
    return ListenableBuilder(
      listenable: widget.playback,
      builder: (context, _) {
        final s = widget.playback.state;
        final error = s.error;
        final ready = s.initialized && error == null && !_opening;
        // 끝까지 가면 멈춘 채 끝에 선다 — 처음 자리로 보이고, 재생을 누르면 처음부터.
        final ended =
            ready &&
            !s.playing &&
            s.duration > Duration.zero &&
            s.position >= s.duration;
        final position = ended ? Duration.zero : s.position;
        final showControls = _controlsVisible || !s.playing;
        return Stack(
          fit: StackFit.expand,
          children: [
            if (!ready) poster else Center(child: widget.playback.buildSurface()),
            if (ready)
              GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: _showControls,
              ),
            if (_opening || (ready && s.buffering))
              const Center(
                child: CircularProgressIndicator(color: AppColors.white),
              )
            else if (error != null && !_opening)
              _ErrorPanel(
                message: widget.errorMessage(error),
                onRetry: _retry,
              )
            else if (ready && showControls)
              Center(
                child: _CenterButton(
                  playing: s.playing,
                  onTap: s.playing ? _pause : _play,
                ),
              ),
            if (ready && showControls)
              Positioned(
                left: AppSpacing.lg,
                right: AppSpacing.lg,
                bottom: AppSpacing.md,
                child: _ProgressRow(
                  position: position,
                  duration: s.duration,
                  onSeek: (dx, width) => _seekAt(dx, width, s.duration),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _CenterButton extends StatelessWidget {
  const _CenterButton({required this.playing, required this.onTap});

  final bool playing;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Pressable(
    semanticLabel: playing ? AppStrings.pauseVideo : AppStrings.playVideo,
    onTap: onTap,
    child: Icon(
      playing ? Icons.pause_circle_filled : Icons.play_circle_fill,
      size: 56,
      color: AppColors.white,
    ),
  );
}

/// 얇은 진행 막대(누르거나 끌어 옮김)와 남은 시간("-0:31").
class _ProgressRow extends StatelessWidget {
  const _ProgressRow({
    required this.position,
    required this.duration,
    required this.onSeek,
  });

  final Duration position;
  final Duration duration;
  final void Function(double dx, double width) onSeek;

  @override
  Widget build(BuildContext context) {
    final total = duration.inMilliseconds;
    final fraction = total == 0
        ? 0.0
        : (position.inMilliseconds / total).clamp(0.0, 1.0);
    final remaining = duration - position;
    return Row(
      children: [
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth;
              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapDown: (d) => onSeek(d.localPosition.dx, width),
                onHorizontalDragUpdate: (d) =>
                    onSeek(d.localPosition.dx, width),
                // 막대는 3pt 지만 누를 자리는 넉넉히.
                child: SizedBox(
                  height: 24,
                  child: Center(
                    child: Container(
                      height: 3,
                      color: AppColors.white.withValues(alpha: 0.4),
                      alignment: Alignment.centerLeft,
                      child: FractionallySizedBox(
                        widthFactor: fraction,
                        child: Container(color: AppColors.white),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Text(
          '-${formatDuration(remaining.inSeconds)}',
          style: AppTypography.caption.copyWith(color: AppColors.white),
        ),
      ],
    );
  }
}

/// 포스터 위 반투명 판 — 원인 문구와 [다시 시도].
class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Container(
    color: AppColors.ink.withValues(alpha: 0.6),
    padding: const EdgeInsets.all(AppSpacing.lg),
    alignment: Alignment.center,
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          message,
          style: AppTypography.body.copyWith(color: AppColors.white),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.md),
        AppButton(label: AppStrings.retry, onPressed: onRetry),
      ],
    ),
  );
}
