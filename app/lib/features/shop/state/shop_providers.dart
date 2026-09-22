import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../api/shop_api.dart';

final shopApiProvider = Provider<ShopApi>(
  (ref) => ShopApi(ref.watch(apiClientProvider)),
);
