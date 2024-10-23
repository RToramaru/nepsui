import os
import sys
import io
import webbrowser
import threading
from django.core.management import execute_from_command_line


def run_server():
    """Run the Django server."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nepsui.settings')

    # Redefine sys.stdout and sys.stderr
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    try:
        execute_from_command_line(["manage.py", "runserver", "--noreload"])
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")


def open_browser():
    """Open the default browser with the Django server URL."""
    import time
    time.sleep(5)  # Wait for the server to start
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == '__main__':
    # Start the server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    # Open the browser
    # open_browser()