@echo off
REM ============================================================
REM 工具链安装脚本 · miku-fps 项目
REM 用途：安装 Blender（本地 MSI，无需联网）
REM 运行：右键"以管理员身份运行"，或 cmd /c setup_blender.bat
REM ============================================================

setlocal
set MSI="C:\Users\Administrator\Downloads\blender-5.2.2-windows-x64.msi"
set TARGET="C:\Program Files\Blender Foundation\Blender 5.2"

echo ============================================================
echo  miku-fps 工具链安装
echo ============================================================
echo.

REM --- 检查 MSI 是否存在 ---
if not exist %MSI% (
    echo [X] 找不到安装包: %MSI%
    echo     请确认文件仍在原位置。
    pause
    exit /b 1
)

echo [1/3] 安装包校验通过: %MSI%
echo.

REM --- 安装（静默模式）---
echo [2/3] 正在安装 Blender 5.2（约 1.5GB，请耐心等待）...
echo       静默安装中，不会有界面...
msiexec /i %MSI% /qn /norestart TARGETDIR=%TARGET% /l*v "%TEMP%\blender_install.log"

if errorlevel 1 (
    echo.
    echo [X] 安装失败。错误日志: %TEMP%\blender_install.log
    echo     常见原因：需要管理员权限。请右键本脚本"以管理员身份运行"。
    pause
    exit /b 1
)

echo [3/3] 验证安装结果...
if exist "%TARGET%\blender.exe" (
    echo.
    echo ============================================================
    echo  [OK] Blender 安装成功
    echo  路径: %TARGET%\blender.exe
    echo.
    echo  下一步：
    echo    1. 安装 Source 2 Viewer（需联网，GitHub 下载）
    echo    2. 用 S2V 导出 CS2 干员模型为 glTF
    echo    3. 打开 Blender，导入两个模型，运行：
    echo       blender\retarget_cs2_to_miku.py
    echo ============================================================
) else (
    echo [!] 未在预期路径找到 blender.exe
    echo     请检查实际安装位置：
    dir /b "C:\Program Files\Blender Foundation\" 2>nul
)

echo.
pause
endlocal
