import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:varedura_mobile/main.dart';

void main() {
  testWidgets('Varedura Mobile Suite renders with 3 navigation destinations',
      (WidgetTester tester) async {
    await tester.pumpWidget(const VareduraMobileApp());
    await tester.pump();

    // Verify AppBar Title
    expect(find.text('SMART CAMERA HUB'), findsOneWidget);

    // Verify Navigation Destinations
    expect(find.text('Cameras'), findsOneWidget);
    expect(find.text('Diagnostics'), findsOneWidget);
    expect(find.text('Node Manager'), findsOneWidget);

    // Tap on Diagnostics Tab
    await tester.tap(find.text('Diagnostics'));
    await tester.pump();

    expect(find.text('NETWORK DIAGNOSTICS'), findsOneWidget);

    // Tap on Node Manager Tab
    await tester.tap(find.text('Node Manager'));
    await tester.pump();

    expect(find.text('REMOTE NODE MANAGER'), findsOneWidget);
  });
}
