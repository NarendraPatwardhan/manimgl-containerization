#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def main():
    # Run the manimgl command
    cmd = [
        "bash", "-c",
        "xvfb-run -s '-screen 0 1920x1080x24' manimgl main.py PrimaryScene -qmw"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)
    
    # Check if the video file exists
    video_path = Path("./videos/PrimaryScene.mp4")
    if not video_path.exists():
        print(f"Error: Expected video file not found at {video_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Success! Video created at {video_path}")
    sys.exit(0)

if __name__ == "__main__":
    main()
