import http.server
import socketserver
import urllib.request
import os

print("Downloading real camera snapshot...")
req = urllib.request.Request(
    "https://dummyimage.com/800x600/1c222d/00e5ff.png&text=Live+Traffic+Feed",
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req) as response, open("snapshot.png", "wb") as out_file:
    out_file.write(response.read())

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if '/snapshot' in self.path:
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.end_headers()
            with open("snapshot.png", "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{}')

# Enable reuse address to prevent "address already in use" errors
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", 8420), Handler) as httpd:
    print("Serving fake camera API on port 8420")
    httpd.serve_forever()
