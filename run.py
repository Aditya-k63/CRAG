import subprocess
import sys
import time

def start_services():
    print("🚀 Starting Backend FastAPI Server...")
    # Launch FastAPI on port 8000 using uvicorn
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"
    ])

    # Wait 3 seconds to let the backend warm up
    time.sleep(3)

    print("🎨 Starting Frontend Streamlit Server...")
    # Launch Streamlit on port 10000 (Render's default public web port)
    frontend_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "10000",
        "--server.address", "0.0.0.0"
    ])

    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("🛑 Shutting down services...")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    start_services()