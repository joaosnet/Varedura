import os
import urllib.request

urls = {
    'driveway': 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=800&q=80',  # Cars / road / driveway
    'front_porch': 'https://images.unsplash.com/photo-1513694203232-719a280e022f?w=800&q=80', # House front / porch
    'backyard': 'https://images.unsplash.com/photo-1584463699035-71c1b1dfa539?w=800&q=80',   # Yard / garden perimeter
    'server_room': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80', # Server rack
}

os.makedirs('runtime/cctv_samples', exist_ok=True)
for name, url in urls.items():
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        dest = f'runtime/cctv_samples/{name}.jpg'
        with urllib.request.urlopen(req, timeout=10) as resp, open(dest, 'wb') as f:
            f.write(resp.read())
        size = os.path.getsize(dest)
        print(f'Successfully downloaded {name}.jpg ({size} bytes)')
    except Exception as e:
        print(f'Failed {name}: {e}')
