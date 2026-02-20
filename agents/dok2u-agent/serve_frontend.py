"""
Simple HTTP server for local development.
Serves index.html from templates/ at root and static files from static/.
"""
import http.server
import socketserver
import os
from pathlib import Path
from urllib.parse import unquote

PORT = 3000
BASE_DIR = Path(__file__).parent

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        """Translate URL path to filesystem path."""
        # Decode URL encoding
        path = unquote(path)
        
        # Remove query string
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        
        # Serve index.html at root
        if path == '/' or path == '/index.html':
            file_path = BASE_DIR / 'templates' / 'index.html'
        # Serve static files
        elif path.startswith('/static/'):
            file_path = BASE_DIR / path.lstrip('/')
        # Serve templates
        elif path.startswith('/templates/'):
            file_path = BASE_DIR / path.lstrip('/')
        # For api calls, return without modification (will 404, as expected)
        elif path.startswith('/api/'):
            file_path = BASE_DIR / path.lstrip('/')
        else:
            # Try to serve from root
            file_path = BASE_DIR / path.lstrip('/')
        
        return str(file_path)

if __name__ == '__main__':
    with socketserver.TCPServer(("localhost", PORT), CustomHandler) as httpd:
        print(f"Serving frontend at http://localhost:{PORT}")
        print(f"Backend should be running at http://localhost:8080")
        print(f"Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
