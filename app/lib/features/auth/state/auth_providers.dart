import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../api/auth_api.dart';
import '../api/invite_api.dart';
import '../api/me_api.dart';

final authApiProvider = Provider<AuthApi>(
  (ref) => AuthApi(ref.watch(apiClientProvider)),
);

final meApiProvider = Provider<MeApi>(
  (ref) => MeApi(ref.watch(apiClientProvider)),
);

final inviteApiProvider = Provider<InviteApi>(
  (ref) => InviteApi(ref.watch(apiClientProvider)),
);
