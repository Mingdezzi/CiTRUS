# File path: ui/theme.py (NEW FILE)

class Colors:
    """
    CiTRUS 프로젝트의 모든 UI에서 사용되는 중앙 색상 팔레트입니다.
    """
    # 테마 주요 색상
    WHITE: str = "#ffffff"
    MAIN_RED: str = "#eb6864"
    DARKER_RED: str = "#d0504c"     # 호버/클릭 시
    DARK_TEAL: str = "#1b3d42"      # 헤더, 라벨 텍스트

    # 회색조
    GREY: str = "#898989"
    DARK_GREY: str = "#6c757d"      # 버튼 호버
    SELECTED_BG: str = "#e0e0e0"    # 레이어 리스트 선택

    # 텍스트 기본값
    BLACK: str = "#000000"

    # 추가된 색상 (기존 코드에서 사용된 것들)
    LIGHTBLUE: str = "lightblue"    # 회전 핸들
    BLUE: str = "blue"              # 리사이즈 핸들 테두리
    DARK_TEAL_ACTIVE: str = "#133034" # 버튼 Active