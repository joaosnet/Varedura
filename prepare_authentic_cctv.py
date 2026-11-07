import datetime
import os
import urllib.request
from PIL import Image, ImageDraw, ImageFont

os.makedirs('runtime/cctv_samples', exist_ok=True)
os.makedirs('mobile/assets/cctv', exist_ok=True)

urls = {
    'driveway': 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=1280&q=85',  # Cars / road / driveway
    'front_porch': 'https://images.unsplash.com/photo-1513694203232-719a280e022f?w=1280&q=85', # House front entrance
    'perimeter': 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=1280&q=85', # House exterior / lawn / perimeter
    'server_room': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1280&q=85', # Data center / server rack
}

cams_info = {
    'driveway': {'ch': 'CAM-01', 'name': 'DRIVEWAY PERIMETER [P2P/NetIP]', 'res': '2560x1440 30FPS', 'codec': 'H.265+ 4096Kbps'},
    'front_porch': {'ch': 'CAM-02', 'name': 'FRONT PORCH / ENTRANCE', 'res': '1920x1080 25FPS', 'codec': 'H.265 2048Kbps'},
    'perimeter': {'ch': 'CAM-03', 'name': 'NORTH FENCE LINE', 'res': '2560x1440 30FPS', 'codec': 'H.265+ 3072Kbps'},
    'server_room': {'ch': 'CAM-04', 'name': 'SERVER RACK & UPS NODE', 'res': '1920x1080 30FPS', 'codec': 'H.264 2560Kbps'},
}

for name, url in urls.items():
    raw_path = f'runtime/cctv_samples/raw_{name}.jpg'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        if not os.path.exists(raw_path):
            with urllib.request.urlopen(req, timeout=15) as resp, open(raw_path, 'wb') as f:
                f.write(resp.read())
        
        img = Image.open(raw_path).convert('RGB')
        img = img.resize((1280, 720), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(img)

        info = cams_info[name]
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Top Bar: Timestamp and Camera Name
        draw.rectangle([(0, 0), (1280, 40)], fill=(0, 0, 0, 160))
        draw.ellipse([(16, 14), (28, 26)], fill=(0, 230, 118)) # REC green dot
        draw.text((36, 12), f"REC  {info['ch']} • {info['name']}", fill=(255, 255, 255))
        draw.text((1050, 12), now_str, fill=(0, 229, 255))

        # Bottom Bar: Bitrate & Codec stats
        draw.rectangle([(0, 680), (1280, 720)], fill=(0, 0, 0, 160))
        draw.text((20, 692), f"BITRATE: {info['codec']}  |  RES: {info['res']}", fill=(200, 200, 200))
        draw.text((1080, 692), "VAREDURA CCTV ENGINE", fill=(0, 230, 118))

        out_path = f'runtime/cctv_samples/{name}.jpg'
        img.save(out_path, 'JPEG', quality=92)
        img.save(f'mobile/assets/cctv/{name}.jpg', 'JPEG', quality=92)
        print(f"Generated realistic CCTV frame: {out_path} ({os.path.getsize(out_path)} bytes)")
    except Exception as e:
        print(f"Failed processing {name}: {e}")
