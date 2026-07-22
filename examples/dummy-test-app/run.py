"""
DigiPay Chat SDK - Dummy App Quick Launcher
Launches a local HTTP server and opens the test application in your default browser.
"""

import sys
import os
import http.server
import socketserver
import webbrowser
import threading

PORT = 8080
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress detailed HTTP logs for clean output

def start_server():
    os.chdir(repo_root)
    with socketserver.TCPServer(("", PORT), QuietHTTPHandler) as httpd:
        httpd.serve_forever()

def main():
    print("==================================================")
    print("DigiPay Chat SDK — Dummy App Quick Launcher")
    print("==================================================")
    print(f"Server starting on http://127.0.0.1:{PORT}")
    
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{PORT}/examples/dummy-test-app/index.html"
    print(f"Opening sandbox application: {url}")
    webbrowser.open(url)

    print("\nPress Ctrl+C to stop the test server.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nTest server stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
