/// Real Flutter UI Simulator Screenshot Capture Engine
/// Renders actual Flutter widgets with full theme, models, and custom painters
/// directly into real pixel-perfect PNG screenshot files using tester.runAsync.

import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:varedura_mobile/core/theme.dart';
import 'package:varedura_mobile/features/cameras/camera_grid_view.dart';
import 'package:varedura_mobile/features/cameras/camera_player_view.dart';
import 'package:varedura_mobile/features/diagnostics/diagnostics_view.dart';
import 'package:varedura_mobile/features/node_manager/node_manager_view.dart';
import 'user_journey_e2e_test.dart';

void main() {
  final outputDir = Directory('C:/Users/joaod/Documents/GitHub/Varedura/screenshots');
  if (!outputDir.existsSync()) {
    outputDir.createSync(recursive: true);
  }

  setUpAll(() {
    // Allow real HTTP requests to our local mock python server (port 8420)
    HttpOverrides.global = null;
  });

  Future<void> captureWidget({
    required WidgetTester tester,
    required Widget widget,
    required String filename,
    Size size = const Size(412, 892),
  }) async {
    final boundaryKey = GlobalKey();

    tester.view.physicalSize = size * 2.0;
    tester.view.devicePixelRatio = 2.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: VareduraTheme.darkTheme,
        home: Scaffold(
          body: Center(
            child: RepaintBoundary(
              key: boundaryKey,
              child: SizedBox(
                width: size.width,
                height: size.height,
                child: widget,
              ),
            ),
          ),
        ),
      ),
    );

    // Give time for Image.network to fetch and render
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();

    await tester.runAsync(() async {
      // Let the real network request complete if it hasn't
      await Future.delayed(const Duration(milliseconds: 500));
      
      final boundary =
          boundaryKey.currentContext!.findRenderObject() as RenderRepaintBoundary;
      final ui.Image image = await boundary.toImage(pixelRatio: 2.0);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      final pngBytes = byteData!.buffer.asUint8List();

      final file = File('${outputDir.path}/$filename.png');
      file.writeAsBytesSync(pngBytes);
      print('[+] Real Flutter Simulator Screenshot: ${file.path} (${pngBytes.length} bytes)');

      // Also copy to brain artifacts directory
      final brainFile = File('C:/Users/joaod/.gemini/antigravity/brain/2146c8aa-f525-4fdc-9021-9f271a4786a4/$filename.png');
      brainFile.writeAsBytesSync(pngBytes);
    });
  }

  testWidgets('Capture Real Flutter Screen 1: Camera Grid View', (tester) async {
    final mockApi = MockVareduraApiClient();
    await captureWidget(
      tester: tester,
      widget: CameraGridView(apiClient: mockApi),
      filename: 'mobile_camera_grid',
    );
  });

  testWidgets('Capture Real Flutter Screen 2: Camera Player with AI & PTZ', (tester) async {
    final mockApi = MockVareduraApiClient();
    final cams = await mockApi.fetchCameras();
    await captureWidget(
      tester: tester,
      widget: CameraPlayerView(
        camera: cams.first,
        apiClient: mockApi,
        autoRefresh: false,
      ),
      filename: 'mobile_camera_player',
    );
  });

  testWidgets('Capture Real Flutter Screen 3: Network Diagnostics & Speedtest', (tester) async {
    final mockApi = MockVareduraApiClient();
    await captureWidget(
      tester: tester,
      widget: DiagnosticsView(
        apiClient: mockApi,
        enablePingMonitor: false,
      ),
      filename: 'mobile_diagnostics',
    );
  });

  testWidgets('Capture Real Flutter Screen 4: Remote Node Manager & Docker Cleaner', (tester) async {
    final mockApi = MockVareduraApiClient();
    await captureWidget(
      tester: tester,
      widget: NodeManagerView(
        apiClient: mockApi,
        enableAutoRefresh: false,
      ),
      filename: 'mobile_node_manager',
    );
  });
}
