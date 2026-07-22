from http.server import HTTPServer, BaseHTTPRequestHandler
import sys, os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

# спользуем PORT из Render (обычно 10000), сигнальный сервер будет на 8080
port = int(os.environ.get('PORT', 10000))
print(f"Health server starting on port {port}")
HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()
