/// Comprehensive End-to-End Realistic User Journey Tests (AAA Quality Assurance)

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:varedura_mobile/core/api_client.dart';
import 'package:varedura_mobile/core/models.dart';
import 'package:varedura_mobile/features/cameras/camera_player_view.dart';
import 'package:varedura_mobile/features/cameras/ptz_joystick_widget.dart';
import 'package:varedura_mobile/features/diagnostics/diagnostics_view.dart';
import 'package:varedura_mobile/features/node_manager/node_manager_view.dart';
import 'package:varedura_mobile/main.dart';

class MockVareduraApiClient extends VareduraApiClient {
  List<String> ptzCommandsSent = [];
  bool cleanupTriggered = false;
  List<String> cleanupSteps = [];

  MockVareduraApiClient() : super(baseUrl: 'http://mock-daemon:8420');

  @override
  Future<bool> checkHealth() async => true;

  @override
  Future<List<CameraModel>> fetchCameras() async {
    return [
      CameraModel(
        id: 'cam_driveway',
        name: 'Driveway Camera',
        protocol: 'icsee',
        ip: '192.168.1.100',
        port: 34567,
        isOnline: true,
        codec: 'h265',
        resolution: '2560x1440',
        streamUrl: 'rtsp://admin:@192.168.1.100:554/stream0',
        ptzSupported: true,
        audioSupported: true,
        activeDetections: [
          DetectionModel(
            classId: 0,
            className: 'person',
            confidence: 0.94,
            bbox: [0.3, 0.2, 0.6, 0.8],
            centroid: [0.45, 0.5],
            timestamp: 1700000000.0,
          ),
          DetectionModel(
            classId: 2,
            className: 'car',
            confidence: 0.89,
            bbox: [0.1, 0.4, 0.4, 0.9],
            centroid: [0.25, 0.65],
            timestamp: 1700000000.0,
          ),
        ],
        recentEvents: [
          AnomalyEventModel(
            ruleId: 'rule_tripwire_gate',
            ruleName: 'Perimeter Tripwire',
            cameraId: 'cam_driveway',
            severity: 'critical',
            message: 'Vehicle crossed perimeter entry gate',
            detection: DetectionModel(
              classId: 2,
              className: 'car',
              confidence: 0.89,
              bbox: [0.1, 0.4, 0.4, 0.9],
              centroid: [0.25, 0.65],
              timestamp: 1700000000.0,
            ),
            timestamp: 1700000000.0,
          ),
        ],
      ),
    ];
  }

  @override
  Future<bool> sendPtzCommand(String cameraId, String command, {int step = 4}) async {
    ptzCommandsSent.add('$cameraId:$command');
    return true;
  }

  @override
  Future<double?> pingHost(String host) async => 14.2;

  @override
  Future<List<String>> scanSubnet(String base) async {
    return ['$base.1', '$base.50', '$base.100'];
  }

  @override
  Future<SystemStatsModel?> fetchSystemStats() async {
    return SystemStatsModel(
      uptimeSeconds: 7200,
      cpuPercent: 24.5,
      memoryUsedMb: 7800,
      memoryTotalMb: 16384,
      memoryPercent: 48.0,
      diskUsedGb: 125.0,
      diskTotalGb: 300.0,
      diskPercent: 42.0,
      pingMs: 14.2,
      gateway: '192.168.1.1',
    );
  }

  @override
  Future<DockerStatusModel?> fetchDockerStatus() async {
    return DockerStatusModel(
      available: true,
      vhdxSizeBytes: 15000000000,
      vhdxFilesCount: 2,
      cleanupProgress: {
        'status': 'Pruned 4 containers, freed 2.4GB',
        'percent': 100,
        'step': 'done',
      },
    );
  }

  @override
  Future<bool> triggerDockerCleanup(List<String> steps) async {
    cleanupTriggered = true;
    cleanupSteps = steps;
    return true;
  }

  @override
  String getSnapshotUrl(String cameraId) {
    // Force the snapshot URL to hit our local python fake camera server
    return 'http://127.0.0.1:8420/snapshot';
  }
}

void main() {
  group('Real User Journey & AAA Quality Assurance Tests', () {
    testWidgets(
        'Journey 1: User navigates cameras, opens player, interacts with PTZ joystick, intercom & zoom',
        (WidgetTester tester) async {
      final mockApi = MockVareduraApiClient();
      final cameras = await mockApi.fetchCameras();
      final cam = cameras.first;

      await tester.pumpWidget(
        MaterialApp(
          home: CameraPlayerView(
            camera: cam,
            apiClient: mockApi,
          ),
        ),
      );
      await tester.pump();

      // 1. Verify player screen titles and live badges
      expect(find.text('Driveway Camera'), findsOneWidget);
      expect(find.text('ICSEE'), findsOneWidget);

      // 2. Toggle AI overlay button
      final aiToggleBtn = find.byTooltip('Toggle AI Overlays');
      expect(aiToggleBtn, findsOneWidget);
      await tester.tap(aiToggleBtn);
      await tester.pump();

      // 3. Interact with PTZ Joystick (tap Up arrow button)
      final joystick = find.byType(PTZJoystickWidget);
      expect(joystick, findsOneWidget);
      await tester.tap(find.byIcon(Icons.arrow_drop_up));
      await tester.pump();
      expect(mockApi.ptzCommandsSent.contains('cam_driveway:DirectionUp'), isTrue);

      // 4. Test Hold-to-Talk 2-Way Audio button
      final talkButton = find.text('HOLD TO TALK');
      expect(talkButton, findsOneWidget);
      await tester.ensureVisible(talkButton);
      await tester.pumpAndSettle();

      final talkGesture = await tester.startGesture(tester.getCenter(talkButton));
      await tester.pump();
      expect(find.text('TALKING...'), findsOneWidget);
      await talkGesture.up();
      await tester.pump();
      expect(find.text('HOLD TO TALK'), findsOneWidget);

      // 5. Test Zoom In / Out controls
      final zoomIn = find.byIcon(Icons.zoom_in);
      await tester.ensureVisible(zoomIn);
      await tester.tap(zoomIn);
      await tester.pump();
      expect(mockApi.ptzCommandsSent.contains('cam_driveway:ZoomIn'), isTrue);

      final zoomOut = find.byIcon(Icons.zoom_out);
      await tester.ensureVisible(zoomOut);
      await tester.tap(zoomOut);
      await tester.pump();
      expect(mockApi.ptzCommandsSent.contains('cam_driveway:ZoomOut'), isTrue);

      // 6. Verify Anomaly Event list
      final eventText = find.text('Vehicle crossed perimeter entry gate');
      await tester.ensureVisible(eventText);
      expect(eventText, findsOneWidget);
    });

    testWidgets(
        'Journey 2: User opens Network Diagnostics, runs subnet scan & bandwidth speedtest',
        (WidgetTester tester) async {
      final mockApi = MockVareduraApiClient();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DiagnosticsView(apiClient: mockApi),
          ),
        ),
      );
      await tester.pump(const Duration(seconds: 1));

      // 1. Verify Ping section renders
      expect(find.text('LIVE PING'), findsOneWidget);

      // 2. Perform Subnet Scan
      final subnetField = find.byType(TextField);
      expect(subnetField, findsOneWidget);
      await tester.enterText(subnetField, '192.168.2');
      await tester.pump();

      final scanBtn = find.text('Scan');
      await tester.tap(scanBtn);
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.text('192.168.2.1'), findsOneWidget);
      expect(find.text('192.168.2.50'), findsOneWidget);
      expect(find.text('192.168.2.100'), findsOneWidget);

      // 3. Trigger Bandwidth Speedtest
      final startTestBtn = find.text('Start Test');
      expect(startTestBtn, findsOneWidget);
      await tester.tap(startTestBtn);
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('Testing...'), findsOneWidget);

      // Advance through simulated speedtest timers (10 * 150ms + 8 * 150ms = ~2700ms)
      for (int i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 200));
      }
      expect(find.text('Start Test'), findsOneWidget);
    });

    testWidgets(
        'Journey 3: User monitors host health, selects Docker filters & triggers remote prune',
        (WidgetTester tester) async {
      final mockApi = MockVareduraApiClient();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NodeManagerView(apiClient: mockApi),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // 1. Verify Host System Health Gauges
      expect(find.text('HOST SYSTEM HEALTH'), findsOneWidget);
      expect(find.text('CPU Usage'), findsOneWidget);
      expect(find.text('RAM Usage'), findsOneWidget);
      expect(find.text('Disk Storage'), findsOneWidget);
      expect(find.text('24.5%'), findsOneWidget);

      // 2. Verify Docker Status & Filter Chips
      expect(find.text('DOCKER ACTIVE'), findsOneWidget);
      expect(find.text('CONTAINERS'), findsOneWidget);
      expect(find.text('IMAGES'), findsOneWidget);

      // Deselect 'VOLUMES' filter chip
      await tester.tap(find.text('VOLUMES'));
      await tester.pump();

      // 3. Trigger Remote Prune
      final pruneBtn = find.text('Trigger Remote Prune');
      expect(pruneBtn, findsOneWidget);
      await tester.tap(pruneBtn);
      await tester.pump(const Duration(milliseconds: 200));

      expect(mockApi.cleanupTriggered, isTrue);
      expect(mockApi.cleanupSteps.contains('volumes'), isFalse);
      expect(mockApi.cleanupSteps.contains('containers'), isTrue);

      // Advance through cleanup polling loops
      for (int i = 0; i < 5; i++) {
        await tester.pump(const Duration(milliseconds: 600));
      }
    });

    testWidgets('Journey 4: User opens Daemon Connection Settings dialog & saves custom IP',
        (WidgetTester tester) async {
      await tester.pumpWidget(const VareduraMobileApp());
      await tester.pump();

      // 1. Tap Settings Icon in AppBar
      final settingsBtn = find.byIcon(Icons.settings_ethernet);
      expect(settingsBtn, findsOneWidget);
      await tester.tap(settingsBtn);
      await tester.pumpAndSettle();

      // 2. Verify Dialog
      expect(find.text('Daemon Connection'), findsOneWidget);
      final ipField = find.byType(TextField);
      await tester.enterText(ipField, 'http://192.168.1.150:8420');
      await tester.pump();

      // 3. Save Dialog
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      // Dialog closed
      expect(find.text('Daemon Connection'), findsNothing);
    });
  });
}
