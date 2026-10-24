"""매장 채널(발신프로필) 연동 상태(설계 4.1)."""
TOKEN_REQUESTED, LINKED, UNLINKED = "token_requested", "linked", "unlinked"
CHANNEL_STATUSES: tuple[str, ...] = (TOKEN_REQUESTED, LINKED, UNLINKED)
