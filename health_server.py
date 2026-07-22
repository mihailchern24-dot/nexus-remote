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

port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', 10000))
HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()
