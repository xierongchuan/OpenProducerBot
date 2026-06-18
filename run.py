#!/usr/bin/env python3
import sys
import os

# Add the current directory to sys.path to make 'src' importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    if os.getenv("SERVO_RUNTIME_SUPERVISOR", "1") == "0":
        from src.main import main
        main()
    else:
        from src.core.runtime_supervisor import main
        main()
