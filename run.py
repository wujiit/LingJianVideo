# Run script for Video Download Assistant
# Usage: python run.py

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from main import main

if __name__ == "__main__":
    main()
