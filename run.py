import subprocess
import time

def run_server():
    """
    Run the FastAPI server using uvicorn.
    """
    print("Starting FastAPI server...")
    server_process = subprocess.Popen(
        ["uvicorn", "server:app", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return server_process

def run_frontend():
    """
    Run the Streamlit frontend application.
    """
    print("Starting Streamlit frontend...")
    frontend_process = subprocess.Popen(
        ["streamlit", "run", "front.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return frontend_process

def main():
    try:
        server_process = run_server()
        # Give the server some time to start
        time.sleep(2)
        frontend_process = run_frontend()
        
        # Wait for both processes to complete (Ctrl+C to exit)
        server_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("Shutting down processes...")
        server_process.terminate()
        frontend_process.terminate()
    except Exception as e:
        print(f"Error occurred: {e}")
        server_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    main()