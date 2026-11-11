def main() -> None:
    print("Hello from teste-streamlit!")
from pathlib import Path
import subprocess
import sys


def main() -> int:
    app_path = Path(__file__).with_name("app.py")
    return subprocess.call(
        [sys.executable, "-m", "streamlit", "run", str(app_path)]
    )
