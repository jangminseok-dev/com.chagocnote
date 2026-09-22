import 'package:flutter/material.dart';

void main() => runApp(const BootstrapApp());

/// 골격만 있는 자리 표시 앱. 라우터가 들어오면(Task 7) 사라진다.
class BootstrapApp extends StatelessWidget {
  const BootstrapApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: '차곡노트',
      home: Scaffold(body: Center(child: Text('차곡노트'))),
    );
  }
}
