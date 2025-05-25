import threading
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_PAYLOAD_SIZE = 8192          # 8 KB
MAX_CONCURRENT_LOG_THREADS = 10  # Max number of concurrent log requests
LOG_REQUEST_TIMEOUT = 2.0        # Max duration per request (in seconds)

def start_gui_log_server(gui_queue, port=5001):
    """Start a web server to capture logs for the GUI."""

    thread_semaphore = threading.BoundedSemaphore(value=MAX_CONCURRENT_LOG_THREADS)

    class LogRequestHandler(BaseHTTPRequestHandler):
        """Class to process http requests for logs"""
        
        def log_message(self, format, *args):
            pass  # suppress console logs

        def do_GET(self):
            """Block GET requests"""
            self.send_response(405)
            self.end_headers()

        def do_PUT(self):
            """Block PUT requets"""
            self.send_response(405)
            self.end_headers()

        def do_POST(self):
            """Process POST requests"""
            
            # Limit thread count
            if not thread_semaphore.acquire(blocking=False):
                self.send_response(429)  # Too Many Requests
                self.end_headers()
                return

            # Enforce timeout per thread
            timer = threading.Timer(LOG_REQUEST_TIMEOUT, self._timeout)
            timer.start()
            
            try:
                # Verify incoming content is type json
                if self.headers.get("Content-Type") != "application/json":
                    self.send_response(400)
                    return

                # Limit content length
                content_len = int(self.headers.get('Content-Length', 0))
                if content_len > MAX_PAYLOAD_SIZE:
                    self.send_response(413)
                    return

                body = self.rfile.read(content_len)
                data = json.loads(body)
                
                # Verify the content is somewhat like we expect.
                if not isinstance(data, dict) or "lines" not in data:
                    raise ValueError("Bad format")

                gui_queue.put(data)
                self.send_response(200)

            except Exception:
                self.send_response(400)
            finally:
                self.end_headers()
                timer.cancel()
                thread_semaphore.release()

        def _timeout(self):
            try:
                self.send_error(408, "Request Timeout")
                self.end_headers()
            except Exception:
                pass  # Ignore errors during timeout handling

    def run():
        server = ThreadingHTTPServer(('localhost', port), LogRequestHandler)
        server.serve_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
