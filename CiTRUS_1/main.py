# 파일 경로: main.py

import sys
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# tkinterdnd2 라이브러리 확인 및 루트 윈도우 설정
try:
    from tkinterdnd2 import TkinterDnD
    DND_ROOT = TkinterDnD.Tk
    print("INFO: 'tkinterdnd2'가 성공적으로 로드되었습니다. 드래그 앤 드롭을 사용할 수 있습니다.")
except ImportError:
    import tkinter as tk
    DND_ROOT = tk.Tk
    print("WARNING: 'tkinterdnd2' 라이브러리가 설치되지 않았습니다. 파일 드래그 앤 드롭을 사용할 수 없습니다.")
    print("         'pip install tkinterdnd2' 명령어로 설치할 수 있습니다.")

# 메인 앱 클래스 임포트
from app import App

def main():
    # 1. 메인 윈도우 생성 (DND 가능 여부에 따라)
    root = DND_ROOT()
    
    # 2. 스타일 설정
    style = ttk.Style(theme='journal')
    style.configure("light.TFrame", background="#ffffff")
    style.configure("light.TLabel", background="#ffffff", foreground="#000000")
    style.configure("light.TCheckbutton", background="#ffffff")
    style.configure("selected.TFrame", background=style.colors.primary)
    style.configure("selected.TLabel", background=style.colors.primary, foreground="#000000")
    style.configure("selected.TCheckbutton", background=style.colors.primary)

    # 3. 윈도우 기본 설정
    root.title("CiTRUS")
    root.geometry("1400x900")
    root.minsize(1200, 800)
    
    # 4. 메인 앱 실행
    App(root)
    
    # 5. 메인 루프 시작
    root.mainloop()

if __name__ == '__main__':
    # --- 프로그램 시작 전 필수 라이브러리 확인 ---
    try:
        import ttkbootstrap
    except ImportError:
        messagebox.showerror("오류", "'ttkbootstrap' 라이브러리가 필요합니다.\n'pip install ttkbootstrap'으로 설치해주세요.")
        sys.exit(1)
    
    try:
        from PIL import Image, ImageTk, ImageDraw, ImageFont
    except ImportError:
        messagebox.showerror("오류", "'Pillow' 라이브러리가 필요합니다.\n'pip install Pillow'으로 설치해주세요.")
        sys.exit(1)
        
    try:
        import rembg
    except ImportError:
        print("WARNING: 'rembg' 라이브러리가 설치되지 않았습니다. 배경제거 기능을 사용할 수 없습니다.")
        print("         'pip install rembg' 명령어로 설치할 수 있습니다.")

    main()