/// 세션을 이루는 모델과 상태.
///
/// `fromJson`은 서버가 주는 스네이크케이스 키를 그대로 읽는다. 토큰은 이
/// 계층에 전혀 나타나지 않는다 — 토큰은 `TokenStore`가 별도로 관리한다.
/// 그래서 `toString`을 오버라이드하지 않아도 민감 정보가 로그에 찍히지
/// 않지만, 그래도 필드를 나열하는 `toString`은 두지 않는다.
class ShopMembership {
  const ShopMembership({
    required this.shopId,
    required this.shopName,
    required this.role,
  });

  factory ShopMembership.fromJson(Map<String, dynamic> json) =>
      ShopMembership(
        shopId: json['shop_id'] as int,
        shopName: json['shop_name'] as String,
        role: json['role'] as String,
      );

  final int shopId;
  final String shopName;

  /// 'owner' | 'staff'
  final String role;

  bool get isOwner => role == 'owner';
}

class Me {
  const Me({
    required this.id,
    required this.displayName,
    required this.profileImageUrl,
    required this.identities,
    required this.shops,
  });

  factory Me.fromJson(Map<String, dynamic> json) => Me(
        id: json['id'] as int,
        displayName: json['display_name'] as String,
        profileImageUrl: json['profile_image_url'] as String?,
        identities: (json['identities'] as List).cast<String>(),
        shops: (json['shops'] as List)
            .map((e) => ShopMembership.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final int id;
  final String displayName;
  final String? profileImageUrl;
  final List<String> identities;
  final List<ShopMembership> shops;
}

/// 세션 자체의 상태. 로딩/에러는 `AsyncValue`가 감싸므로 여기서는
/// "로그아웃"과 "로그인"만 표현한다.
sealed class Session {
  const Session();
}

/// 로그아웃 상태. [sessionExpired]는 HTTP 계층이 리프레시 실패로 세션을
/// 강제 종료했을 때 true가 된다 — 로그인 화면은 이때 "보안을 위해 다시
/// 로그인해 주세요"를 보여준다.
class SignedOut extends Session {
  const SignedOut({this.sessionExpired = false});

  final bool sessionExpired;
}

class SignedIn extends Session {
  const SignedIn({required this.me, required this.selectedShopId});

  final Me me;
  final int? selectedShopId;

  ShopMembership? get selectedShop {
    for (final shop in me.shops) {
      if (shop.shopId == selectedShopId) return shop;
    }
    return null;
  }

  SignedIn copyWith({Me? me, int? selectedShopId}) => SignedIn(
        me: me ?? this.me,
        selectedShopId: selectedShopId ?? this.selectedShopId,
      );
}
