import 'package:flutter_test/flutter_test.dart';
import 'package:varedura_mobile/core/models.dart';

void main() {
  group('Data Models Serialization Tests', () {
    test('DetectionModel correctly parses JSON and converts back', () {
      final jsonMap = {
        'class_id': 0,
        'class_name': 'person',
        'confidence': 0.95,
        'bbox': [0.1, 0.2, 0.5, 0.8],
        'centroid': [0.3, 0.5],
        'track_id': 42,
        'timestamp': 1700000000.0,
      };

      final det = DetectionModel.fromJson(jsonMap);
      expect(det.classId, 0);
      expect(det.className, 'person');
      expect(det.confidence, 0.95);
      expect(det.bbox, [0.1, 0.2, 0.5, 0.8]);
      expect(det.centroid, [0.3, 0.5]);
      expect(det.trackId, 42);

      final outJson = det.toJson();
      expect(outJson['class_name'], 'person');
      expect(outJson['track_id'], 42);
    });

    test('CameraModel correctly parses camera and nested AI detections', () {
      final jsonMap = {
        'id': 'cam_front_door',
        'name': 'Front Door',
        'protocol': 'icsee',
        'ip': '192.168.1.50',
        'port': 34567,
        'is_online': true,
        'codec': 'h265',
        'resolution': '2560x1440',
        'stream_url': 'rtsp://admin:@192.168.1.50:554/stream0',
        'ptz_supported': true,
        'audio_supported': true,
        'ai': {
          'active_detections': [
            {
              'class_id': 0,
              'class_name': 'person',
              'confidence': 0.88,
              'bbox': [0.2, 0.2, 0.6, 0.7],
              'centroid': [0.4, 0.45],
              'track_id': 1,
              'timestamp': 1700000010.0,
            }
          ],
          'recent_events': [
            {
              'rule_id': 'rule_tripwire',
              'rule_name': 'Gate Tripwire',
              'camera_id': 'cam_front_door',
              'severity': 'warning',
              'message': 'Person crossed tripwire',
              'detection': {
                'class_id': 0,
                'class_name': 'person',
                'confidence': 0.88,
                'bbox': [0.2, 0.2, 0.6, 0.7],
                'centroid': [0.4, 0.45],
                'timestamp': 1700000010.0,
              },
              'timestamp': 1700000010.0,
            }
          ]
        }
      };

      final cam = CameraModel.fromJson(jsonMap);
      expect(cam.id, 'cam_front_door');
      expect(cam.name, 'Front Door');
      expect(cam.protocol, 'icsee');
      expect(cam.isOnline, true);
      expect(cam.ptzSupported, true);
      expect(cam.audioSupported, true);
      expect(cam.activeDetections.length, 1);
      expect(cam.recentEvents.length, 1);
      expect(cam.recentEvents.first.severity, 'warning');
    });

    test('SystemStatsModel correctly parses host system metrics', () {
      final jsonMap = {
        'uptime_seconds': 3600,
        'cpu_percent': 14.5,
        'memory': {
          'total_mb': 16384,
          'used_mb': 8192,
          'percent': 50.0,
        },
        'disk': {
          'total_gb': 512.0,
          'used_gb': 256.0,
          'percent': 50.0,
        },
        'network': {
          'ping_ms': 12.3,
          'gateway': '192.168.1.1',
        }
      };

      final stats = SystemStatsModel.fromJson(jsonMap);
      expect(stats.uptimeSeconds, 3600);
      expect(stats.cpuPercent, 14.5);
      expect(stats.memoryUsedMb, 8192);
      expect(stats.pingMs, 12.3);
      expect(stats.gateway, '192.168.1.1');
    });
  });
}
