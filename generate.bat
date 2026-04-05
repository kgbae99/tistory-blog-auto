@echo off
chcp 65001 > nul
cd /d C:\Users\CleanAdmin\Desktop\claude\blog

echo ================================
echo   블로그 포스트 생성 도구
echo ================================
echo.
echo [1] 건강 블로그 생성
echo [2] IT 블로그 생성
echo [3] 건강 + IT 전체 생성
echo.
set /p choice="선택 (1~3): "

if "%choice%"=="1" goto health
if "%choice%"=="2" goto it
if "%choice%"=="3" goto all
goto end

:health
echo.
echo [건강] 키워드 생성 중...
python scripts/step3_generate.py --blog health
echo.
echo [건강] 리라이팅 + HTML 조립 중...
python scripts/step4_rewrite.py --blog health
goto end

:it
echo.
echo [IT] 키워드 생성 중...
python scripts/step3_generate.py --blog it
echo.
echo [IT] 리라이팅 + HTML 조립 중...
python scripts/step4_rewrite.py --blog it
goto end

:all
echo.
echo [건강] 키워드 생성 중...
python scripts/step3_generate.py --blog health
echo.
echo [건강] 리라이팅 + HTML 조립 중...
python scripts/step4_rewrite.py --blog health
echo.
echo [IT] 키워드 생성 중...
python scripts/step3_generate.py --blog it
echo.
echo [IT] 리라이팅 + HTML 조립 중...
python scripts/step4_rewrite.py --blog it
goto end

:end
echo.
echo 생성 완료!
pause