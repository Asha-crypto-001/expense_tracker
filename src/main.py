import sys
import os

# Add the project root to sys.path so 'src' can be resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.app import main

if __name__ == "__main__":
    main()


