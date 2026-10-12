"""
Root Launcher for Lab 5 Ludo:
Allows running 'python ludo.py' directly from the repository root.
"""
import os
import sys

lab5_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Lab5(ludo with bluetooth)")
if lab5_dir not in sys.path:
    sys.path.insert(0, lab5_dir)

os.chdir(lab5_dir)
import ludo

if __name__ == "__main__":
    ludo.main()
