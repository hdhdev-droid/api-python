"""
프로젝트 루트에서 실행: python run.py
"""
import sys
import os

# 프로젝트 루트를 path에 추가하고 src에서 앱 실행
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# src.app의 main 실행
from src.app import main

if __name__ == "__main__":
    main()
