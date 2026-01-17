# 파일 경로: services/font_service.py

import sys
import os
from functools import lru_cache

class FontService:
    """
    운영체제에 맞는 폰트 경로를 관리하고 제공하는 클래스
    """
    @staticmethod
    @lru_cache(maxsize=None)
    def get_font_path(font_name: str) -> str:
        """
        주어진 폰트 이름에 대한 전체 경로를 반환합니다.
        lru_cache를 사용하여 반복적인 파일 시스템 조회를 피합니다.
        """
        if not font_name.lower().endswith(('.ttf', '.otf')):
            font_name += '.ttf'

        if sys.platform == "win32":
            font_dir = os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Fonts")
        elif sys.platform == "darwin": # macOS
            font_dir = "/System/Library/Fonts/Supplemental" 
        else: # Linux
            font_dir = "/usr/share/fonts/truetype"

        path = os.path.join(font_dir, font_name)
        if os.path.exists(path):
            return path
        
        # 대체 폰트 경로 (Linux의 다른 경로 등)
        if sys.platform.startswith("linux"):
            alt_path = os.path.join("/usr/share/fonts/liberation", font_name)
            if os.path.exists(alt_path):
                return alt_path

        # 기본 폰트 (맑은 고딕)
        default_font = "malgun.ttf"
        default_path = os.path.join(font_dir, default_font)
        if os.path.exists(default_path):
            return default_path
        
        # 최후의 수단
        print(f"WARNING: '{font_name}' 폰트를 찾을 수 없어 기본값을 반환합니다.")
        return default_font # Tkinter가 내부적으로 찾도록 이름만 반환