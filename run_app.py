#!/usr/bin/env python
"""Run the Elektraz Streamlit application."""

import subprocess
import sys
from pathlib import Path

def main():
    app_path = Path(__file__).parent / "app" / "app.py"
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", "8501",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]
    
    print("Starting Elektraz Dashboard...")
    print(f"Open http://localhost:8501 in your browser")
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
