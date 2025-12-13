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
        if not isinstance(font_name, str): # 안전 장치
             font_name = 'malgun.ttf'

        if not font_name.lower().endswith(('.ttf', '.otf')):
            font_name += '.ttf'

        font_dirs = []
        if sys.platform == "win32":
            font_dirs.append(os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Fonts"))
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                 font_dirs.append(os.path.join(local_app_data, "Microsoft", "Windows", "Fonts"))

        elif sys.platform == "darwin": # macOS
            font_dirs.append("/System/Library/Fonts/Supplemental")
            font_dirs.append("/Library/Fonts")
            font_dirs.append(os.path.join(os.path.expanduser("~"), "Library", "Fonts"))
        else: # Linux
            font_dirs.append("/usr/share/fonts/truetype")
            font_dirs.append("/usr/local/share/fonts")
            font_dirs.append(os.path.join(os.path.expanduser("~"), ".fonts"))
            font_dirs.append("/usr/share/fonts/liberation") # 특정 폰트 경로 추가

        # 지정된 폰트 찾기
        for font_dir in font_dirs:
            path = os.path.join(font_dir, font_name)
            if os.path.exists(path):
                return path

        # 폴백 폰트 (맑은 고딕 또는 기본값)
        default_font = "malgun.ttf" if sys.platform == "win32" else "LiberationSans-Regular.ttf" # Linux 기본값 예시
        for font_dir in font_dirs:
             default_path = os.path.join(font_dir, default_font)
             if os.path.exists(default_path):
                 print(f"경고: '{font_name}' 폰트를 찾을 수 없어 '{default_font}'로 대체합니다.")
                 return default_path

        # 최후의 수단 (Tkinter가 내부적으로 찾도록 이름만 반환)
        print(f"경고: '{font_name}' 폰트를 시스템에서 찾을 수 없습니다. Tkinter 기본 폰트를 사용합니다.")
        return font_name # Tkinter가 알아서 처리하도록 이름만 반환 (오류 발생 가능성 있음)
