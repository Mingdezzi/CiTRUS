@echo off
rem 현재 배치 파일이 있는 폴더부터 재귀적으로 모든 __pycache__ 폴더 삭제
setlocal enabledelayedexpansion
for /d /r "%~dp0" %%D in (__pycache__) do (
    echo Removing "%%~fD"
    rmdir /s /q "%%~fD"
)
endlocal
