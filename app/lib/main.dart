import 'package:flutter/material.dart';

import 'app.dart';
import 'design/bridge/glass_setup.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeGlass();
  runApp(buildRoot());
}
