@echo off
:: ===========================================================
:: 프로젝트 폴더 구조 자동 생성 스크립트
:: 프로젝트 루트: CiTRUS
:: ===========================================================

set "ROOT=CiTRUS"

echo [1/4] 프로젝트 루트 생성 중...
mkdir "%ROOT%"

echo [2/4] 기본 파일 생성 중...
type nul > "%ROOT%\main.py"
type nul > "%ROOT%\app.py"

echo [3/4] 하위 폴더 구조 생성 중...
mkdir "%ROOT%\tabs"
mkdir "%ROOT%\tabs\easel"
mkdir "%ROOT%\tabs\easel\components"
mkdir "%ROOT%\tabs\easel\models"
mkdir "%ROOT%\tabs\stitch"
mkdir "%ROOT%\tabs\lab"
mkdir "%ROOT%\ui"
mkdir "%ROOT%\services"
mkdir "%ROOT%\models"

echo [4/4] 빈 파일 생성 중...
:: tabs 폴더
type nul > "%ROOT%\tabs\__init__.py"

:: easel 폴더
type nul > "%ROOT%\tabs\easel\__init__.py"
type nul > "%ROOT%\tabs\easel\easel_tab_view.py"
type nul > "%ROOT%\tabs\easel\easel_controller.py"
type nul > "%ROOT%\tabs\easel\canvas_controller.py"
type nul > "%ROOT%\tabs\easel\event_handler.py"

:: easel/components 폴더
type nul > "%ROOT%\tabs\easel\components\__init__.py"
type nul > "%ROOT%\tabs\easel\components\layer_list.py"

:: easel/models 폴더
type nul > "%ROOT%\tabs\easel\models\__init__.py"
type nul > "%ROOT%\tabs\easel\models\layer.py"

:: stitch 폴더
type nul > "%ROOT%\tabs\stitch\__init__.py"
type nul > "%ROOT%\tabs\stitch\stitch_tab_view.py"
type nul > "%ROOT%\tabs\stitch\stitch_controller.py"

:: lab 폴더
type nul > "%ROOT%\tabs\lab\__init__.py"
type nul > "%ROOT%\tabs\lab\lab_tab_view.py"
type nul > "%ROOT%\tabs\lab\lab_controller.py"

:: ui 폴더
type nul > "%ROOT%\ui\dialogs.py"

:: services 폴더
type nul > "%ROOT%\services\__init__.py"
type nul > "%ROOT%\services\project_service.py"
type nul > "%ROOT%\services\image_service.py"
type nul > "%ROOT%\services\font_service.py"

:: models 폴더
type nul > "%ROOT%\models\__init__.py"

echo.
echo ✅ 폴더 및 파일 생성 완료: %ROOT%
pause
