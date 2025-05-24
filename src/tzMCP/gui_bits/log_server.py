import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

def start_gui_log_server(gui_queue, port=5001):
    class LogRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # suppress console output

        def do_POST(self):
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            try:
                data = json.loads(body)
                gui_queue.put(data)
                self.send_response(200)
            except Exception:
                self.send_response(400)
            self.end_headers()

    def run():
        server = HTTPServer(('localhost', port), LogRequestHandler)
        server.serve_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
