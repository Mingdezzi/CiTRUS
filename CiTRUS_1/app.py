# 파일 경로: app.py

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# 탭 폴더에서 EaselTab 클래스를 가져옵니다.
from tabs.easel_tab import EaselTab

class App(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.pack(fill=BOTH, expand=YES)
        self._build_layout()

    def _build_layout(self):
        # 1. 헤더 프레임
        header_frame = ttk.Frame(self, padding=(10, 10))
        header_frame.pack(side="top", fill="x", pady=(0, 0))
        ttk.Label(header_frame, text="CiTRUS", font=("", 16, "bold")).pack(anchor="w")

        # 2. 메인 영역 프레임 (탭이 들어갈 공간)
        main_area_frame = ttk.Frame(self)
        main_area_frame.pack(side="top", fill="both", expand=True, padx=10, pady=0)

        # 3. 탭 관리자(Notebook) 생성
        notebook = ttk.Notebook(main_area_frame)
        notebook.pack(fill="both", expand=True)

        # 4. Easel 탭 생성 및 추가
        easel_tab = EaselTab(notebook, padding=0)
        notebook.add(easel_tab, text="🎨 Easel")

        # 5. 푸터 프레임
        under_frame = ttk.Frame(self, padding=(0, 0))
        under_frame.pack(side="bottom", fill="x")
        ttk.Separator(under_frame, bootstyle="secondary").pack(fill="x", pady=(0,5))
        ttk.Label(under_frame, text="CiTRUS Made By CODE8251", bootstyle="secondary", anchor="e").pack(fill="x")