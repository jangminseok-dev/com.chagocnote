from __future__ import annotations

from auth.app.dtos.auth_myself_dto import AuthMyselfQuery, AuthMyselfResponse
from auth.app.ports.input.auth_myself_use_case import AuthMyselfUseCase
from auth.app.ports.output.auth_myself_record_port import AuthMyselfRecordPort


class AuthMyselfInteractor(AuthMyselfUseCase):
    def __init__(self, record: AuthMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: AuthMyselfQuery) -> AuthMyselfResponse:
        await self._record.record(
            subject="introduce_myself", note=f"{query.name} 자기소개 조회"
        )
        return AuthMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "소셜 로그인으로 신원을 확인하고 차곡노트 자체 토큰을 발급합니다. "
                "POST /v1/auth/social 은 카카오·구글·Apple(개발 환경에서는 dev)의 토큰을 받아 "
                "제공자에게 직접 검증한 뒤 액세스 토큰(15분)과 리프레시 토큰(30일)을 돌려줍니다. "
                "POST /v1/auth/refresh 는 리프레시 토큰을 새 토큰으로 바꿉니다. 이미 쓴 토큰이 다시 오면 "
                "탈취로 보고 그 유저의 세션을 모두 폐기합니다. "
                "POST /v1/auth/logout 은 리프레시 토큰을 폐기합니다. "
                "POST /v1/auth/identities 는 로그인한 계정에 로그인 수단을 하나 더 붙이고(제공자마다 하나), "
                "DELETE /v1/auth/identities/{provider} 는 해제하면서 모든 세션을 끊고 새 토큰을 돌려줍니다. "
                "마지막 로그인 수단은 해제할 수 없습니다. "
                "DELETE /v1/auth/account 는 회원 탈퇴입니다. 소속을 해제하고 계정을 익명화하고 신원을 지우며, "
                "혼자 사장인 매장에 다른 멤버가 있으면 409 로 막습니다. "
                "토큰에는 유저 ID만 들어 있고 역할과 권한은 넣지 않습니다. "
                "신원은 제공자에게 직접 확인한 값만 믿으며(Apple 의 표시 이름만 앱이 보낸 값을 씁니다) "
                "카카오·구글 토큰은 저장하지 않습니다."
            ),
        )
