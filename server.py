import os
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

PORT = int(os.environ.get("PORT", 8080))

class Handler(SimpleHTTPRequestHandler):
    pass

with TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Serving 1956 Commons entry page on port {PORT}...")
    httpd.serve_forever()
