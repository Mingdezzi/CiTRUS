# File path: app.py (replace the file's contents completely with this code - No ttkbootstrap)

import tkinter as tk
import tkinter.ttk as ttk # [MODIFIED] 표준 ttk 사용 (Notebook용)
# from ttkbootstrap.constants import * # 더 이상 필요 없음

# [ ★★★★★ NEW: 테마 임포트 ★★★★★ ]
from ui.theme import Colors

# --- Corrected import path for Easel tab view ---
from tabs.easel.easel_tab_view import EaselTabView
# --- End of correction ---

class App(tk.Frame): # [MODIFIED] tk.Frame 상속
    def __init__(self, parent, *args, **kwargs):
        # [MODIFIED] 흰색 배경 적용 (tk 옵션 사용)
        super().__init__(parent, *args, bg=Colors.WHITE, **kwargs) # Use Colors.WHITE
        self.pack(fill=tk.BOTH, expand=tk.YES)
        self._build_layout()

    def _build_layout(self):
        # 1. Header Frame
        header_frame = tk.Frame(self, bg=Colors.WHITE, padx=10, pady=10) # Use Colors.WHITE
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 0))
        tk.Label(header_frame, text="CiTRUS", font=("", 16, "bold"),
                 bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(anchor=tk.W) # Use Colors

        # 2. Main Area Frame (space for tabs)
        main_area_frame = tk.Frame(self, bg=Colors.WHITE) # Use Colors.WHITE
        main_area_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=0)

        # 3. Create Notebook (Tab manager)
        # 스타일은 main.py에서 ttk.Style()로 설정됨
        notebook = ttk.Notebook(main_area_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 4. Create and add Easel tab
        easel_tab = EaselTabView(notebook)
        notebook.add(easel_tab, text="🎨 Easel")

        # --- Location for adding Stitch, Lab tabs in the future ---
        # stitch_tab = StitchTabView(notebook)
        # notebook.add(stitch_tab, text="🧵 Stitch")
        # lab_tab = LabTabView(notebook)
        # notebook.add(lab_tab, text="🔬 Lab")
        # --- ------------------------------------------------- ---

        # 5. Footer Frame
        under_frame = tk.Frame(self, bg=Colors.WHITE) # Use Colors.WHITE
        under_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10)

        separator = tk.Frame(under_frame, height=1, bg=Colors.GREY) # Use Colors.GREY
        separator.pack(fill=tk.X, pady=(0,5))

        tk.Label(under_frame, text="CiTRUS Made By CODE8251",
                 bg=Colors.WHITE, fg=Colors.GREY, anchor=tk.E).pack(fill=tk.X) # Use Colors