import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/error_messages.dart';
import '../../../core/router/screen_keys.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_back_button.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_chip.dart';
import '../../../design/widgets/app_photo_tile.dart';
import '../../../design/widgets/app_sheet.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../api/shop_api.dart';
import '../state/members_controller.dart';

/// 매장 멤버 목록. 사장은 초대 코드 발급과 멤버 관리(역할 변경·내보내기)를
/// 함께 볼 수 있다. 직원은 목록만 본다.
class MembersScreen extends ConsumerStatefulWidget {
  const MembersScreen({super.key});

  @override
  ConsumerState<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends ConsumerState<MembersScreen> {
  String? _errorText;

  int? get _shopId {
    final session = ref.read(sessionControllerProvider).value;
    return session is SignedIn ? session.selectedShopId : null;
  }

  Future<void> _createInvite() async {
    final shopId = _shopId;
    if (shopId == null) return;
    setState(() => _errorText = null);
    try {
      final invite =
          await ref.read(membersControllerProvider(shopId).notifier).createInvite();
      if (!mounted) return;
      _showInviteSheet(invite);
    } catch (e) {
      if (!mounted) return;
      setState(() => _errorText = messageFor(e));
    }
  }

  void _showInviteSheet(CreatedInvite invite) {
    AppSheet.show<void>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            invite.code,
            style: AppTypography.inviteCode,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            '${AppStrings.inviteExpiresAtLabel} ${_formatDateTime(invite.expiresAt)}',
            style: AppTypography.caption,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.copy,
            onPressed: () => Clipboard.setData(ClipboardData(text: invite.code)),
          ),
        ],
      ),
    );
  }

  Future<void> _openMemberActions(ShopMember member) async {
    final action = await AppSheet.show<String>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ActionRow(
            label: member.isOwner
                ? AppStrings.demoteToStaff
                : AppStrings.promoteToOwner,
            onTap: () => Navigator.of(context)
                .pop(member.isOwner ? 'staff' : 'owner'),
          ),
          _ActionRow(
            label: AppStrings.removeMember,
            onTap: () => Navigator.of(context).pop('remove'),
          ),
        ],
      ),
    );
    if (action == null || !mounted) return;

    final shopId = _shopId;
    if (shopId == null) return;

    if (action == 'remove') {
      final confirmed = await _confirmRemove();
      if (confirmed != true || !mounted) return;
      await _run(
        () => ref
            .read(membersControllerProvider(shopId).notifier)
            .remove(member.memberId),
      );
      return;
    }

    await _run(
      () => ref
          .read(membersControllerProvider(shopId).notifier)
          .changeRole(member.memberId, action),
    );
  }

  Future<bool?> _confirmRemove() {
    return AppSheet.show<bool>(
      context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.removeMemberConfirmTitle,
            style: AppTypography.body,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppButton(
            label: AppStrings.removeMember,
            filled: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: AppStrings.cancel,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _errorText = null);
    try {
      await action();
    } catch (e) {
      if (!mounted) return;
      setState(() => _errorText = messageFor(e));
    }
  }

  // 서버는 UTC로 날짜를 준다(`Z` 접미사). `toLocal()` 없이 년·월·일을
  // 그대로 찍으면 한국 시간 기준으로 하루 이른 날짜가 보일 수 있다.
  static String _formatDate(DateTime date) {
    final local = date.toLocal();
    return '${local.year}.${local.month.toString().padLeft(2, '0')}.${local.day.toString().padLeft(2, '0')}';
  }

  static String _formatDateTime(DateTime date) {
    final local = date.toLocal();
    return '${_formatDate(date)} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final shopId = _shopId;
    final session = ref.watch(sessionControllerProvider).value;
    final isOwner =
        session is SignedIn && (session.selectedShop?.isOwner ?? false);
    final myUserId = session is SignedIn ? session.me.id : null;
    final members = shopId == null
        ? const AsyncValue<List<ShopMember>>.data(<ShopMember>[])
        : ref.watch(membersControllerProvider(shopId));

    return Scaffold(
      key: ScreenKeys.settingsMembers,
      body: AppBackground(
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const AppBackButton(),
                        const SizedBox(width: AppSpacing.sm),
                        Text(
                          AppStrings.settingsMembers,
                          style: AppTypography.titleKo,
                        ),
                      ],
                    ),
                    if (isOwner)
                      AppButton(
                        label: AppStrings.createInvite,
                        onPressed: _createInvite,
                      ),
                  ],
                ),
              ),
              if (_errorText != null)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                  ),
                  child: Text(
                    _errorText!,
                    style: AppTypography.caption,
                  ),
                ),
              Expanded(
                child: members.when(
                  data: (list) => ListView.builder(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    itemCount: list.length,
                    itemBuilder: (context, index) {
                      final member = list[index];
                      final isSelf = member.userId == myUserId;
                      final canManage = isOwner && !isSelf;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: Pressable(
                          onTap: canManage
                              ? () => _openMemberActions(member)
                              : null,
                          semanticLabel: member.displayName,
                          child: AppCard(
                            child: Row(
                              children: [
                                AppPhotoTile(
                                  image: member.profileImageUrl != null
                                      ? NetworkImage(member.profileImageUrl!)
                                      : null,
                                  size: 40,
                                ),
                                const SizedBox(width: AppSpacing.md),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        member.displayName,
                                        style: AppTypography.bodyStrong,
                                      ),
                                      Text(
                                        _formatDate(member.joinedAt),
                                        style: AppTypography.caption,
                                      ),
                                    ],
                                  ),
                                ),
                                AppChip(
                                  label: member.isOwner
                                      ? AppStrings.roleOwner
                                      : AppStrings.roleStaff,
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(messageFor(error), style: AppTypography.body),
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: AppStrings.retry,
                          onPressed: () => ref
                              .invalidate(membersControllerProvider(shopId!)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        alignment: Alignment.center,
        child: Text(label, style: AppTypography.body),
      ),
    );
  }
}
