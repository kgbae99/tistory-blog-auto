@echo off
chcp 65001 > nul

set BLOG=C:\Users\CleanAdmin\Desktop\claude\blog
set AUTO=C:\Users\CleanAdmin\Desktop\claude\tistory_auto
set SCRIPTS=%BLOG%\scripts
set CONFIG=%BLOG%\config
set PY=%AUTO%\multi_blog_reserve_upload.py
set AUTH=%AUTO%\save_auth.py

if exist "%SCRIPTS%\multi_blog_reserve_upload.py" set PY=%SCRIPTS%\multi_blog_reserve_upload.py
if exist "%SCRIPTS%\save_auth_cookies.py" set AUTH=%SCRIPTS%\save_auth_cookies.py

:MAIN_MENU
cls
echo.
echo ===========================================
echo   Blog Automation Manager
echo ===========================================
echo.
echo  [1] Generate - Health Blog (3 posts)
echo  [2] Generate - IT Blog (3 posts)
echo  [3] Generate - Health + IT (both)
echo  [A] Generate + Upload - Health News (today)
echo.
echo  [4] Upload   - Health Blog (reserved)
echo  [5] Upload   - IT Blog (reserved)
echo  [6] Upload   - All Blogs (reserved)
echo.
echo  [7] Publish  - Reserve +3h (1 post)
echo.
echo  [8] Auth     - Save login session
echo  [9] Full     - Generate + Upload Health
echo  [0] Full     - Generate + Upload IT
echo.
echo  [Q] Exit
echo.
set choice=
set /p choice=Select: 

if "%choice%"=="1" goto HEALTH_GEN
if "%choice%"=="2" goto IT_GEN
if "%choice%"=="3" goto ALL_GEN
if /i "%choice%"=="A" goto HEALTH_NEWS_FULL
if "%choice%"=="4" goto HEALTH_UPLOAD
if "%choice%"=="5" goto IT_UPLOAD
if "%choice%"=="6" goto ALL_UPLOAD
if "%choice%"=="7" goto INSTANT_PUBLISH
if "%choice%"=="8" goto SAVE_AUTH
if "%choice%"=="9" goto HEALTH_FULL
if "%choice%"=="0" goto IT_FULL
if /i "%choice%"=="Q" goto EXIT
goto MAIN_MENU

:HEALTH_GEN
cls
echo [1] Generating Health Blog posts...
python %SCRIPTS%\generate_daily_posts.py
echo Done!
pause
goto MAIN_MENU

:IT_GEN
cls
echo [2] Generating IT Blog posts...
python %SCRIPTS%\generate_it_posts.py
echo Done!
pause
goto MAIN_MENU

:ALL_GEN
cls
echo [3] Generating both blogs simultaneously...
start "Health-Blog" cmd /k python %SCRIPTS%\generate_daily_posts.py
start "IT-Blog" cmd /k python %SCRIPTS%\generate_it_posts.py
echo Both windows started.
pause
goto MAIN_MENU

:HEALTH_NEWS_FULL
cls
echo [A] Health News: Generate then Upload...
echo.
echo [1/2] Generating today health news...
python %SCRIPTS%\generate_health_news.py
if errorlevel 1 (
    echo.
    echo ERROR: Generate failed! Check API key.
    pause
    goto MAIN_MENU
)
echo.
echo [2/2] Uploading to Tistory (health-news category)...
python %PY% --blog health-news
if errorlevel 1 (
    echo Session expired. Refreshing...
    python %AUTH% --blog health
    python %PY% --blog health-news
)
goto MAIN_MENU

:HEALTH_UPLOAD
cls
echo [4] Uploading Health Blog (reserved)...
python %PY% --blog posts
if errorlevel 1 (
    echo Session expired. Refreshing...
    python %AUTH% --blog health
    python %PY% --blog posts
)
echo Done!
pause
goto MAIN_MENU

:IT_UPLOAD
cls
echo [5] Uploading IT Blog (reserved)...
python %PY% --blog it-posts
if errorlevel 1 (
    echo Session expired. Refreshing...
    python %AUTH% --blog it
    python %PY% --blog it-posts
)
echo Done!
pause
goto MAIN_MENU

:ALL_UPLOAD
cls
echo [6] Uploading All Blogs (reserved)...
python %PY% --blog all
if errorlevel 1 (
    echo Session expired. Refreshing...
    python %AUTH% --blog both
    python %PY% --blog all
)
echo Done!
pause
goto MAIN_MENU

:INSTANT_PUBLISH
cls
echo [7] Reserve +3h (1 post)
echo.
echo  [1] Health Blog (kgbae2369)
echo  [2] IT Blog (uyoblog)
echo  [B] Back
echo.
set blog_choice=
set /p blog_choice=Select: 
if "%blog_choice%"=="1" python %PY% --instant posts
if "%blog_choice%"=="2" python %PY% --instant it-posts
if /i "%blog_choice%"=="B" goto MAIN_MENU
echo Done!
pause
goto MAIN_MENU

:SAVE_AUTH
cls
echo [8] Saving login session...
python %AUTH% --blog both
echo.
echo Auth files saved to:
echo   %CONFIG%\auth_blog.json
echo   %CONFIG%\auth_blog_it.json
echo Done!
pause
goto MAIN_MENU

:HEALTH_FULL
cls
echo [9] Health: Generate then Upload...
python %SCRIPTS%\generate_daily_posts.py
echo Generate done. Starting upload...
python %PY% --blog posts
echo Done!
pause
goto MAIN_MENU

:IT_FULL
cls
echo [0] IT: Generate then Upload...
python %SCRIPTS%\generate_it_posts.py
echo Generate done. Starting upload...
python %PY% --blog it-posts
echo Done!
pause
goto MAIN_MENU

:EXIT
exit
