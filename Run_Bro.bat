@echo off
chcp 65001 >nul
title ব্রো (Bro) v3.0

echo ╔═══════════════════════════════════════════╗
echo ║           🧠 ব্রো (Bro) v3.0                ║
echo ║     সুপারচার্জড AI অ্যাসিস্ট্যান্ট           ║
echo ╚═══════════════════════════════════════════╝
echo.

:: ভার্চুয়াল এনভায়রনমেন্ট অ্যাক্টিভেট
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo ⚠ .venv পাওয়া যায়নি — প্রথমে Setup_Bro.bat চালান
    pause
    exit /b 1
)

:: .env চেক
if not exist ".env" (
    echo ⚠ .env ফাইল নেই — প্রথমে Setup_Bro.bat চালান
    pause
    exit /b 1
)

:: মোড সিলেক্ট
echo চালানোর মোড বেছে নিন:
echo   [1] ইন্টারেক্টিভ মোড (টেক্সট চ্যাট)
echo   [2] লিসেনার মোড (ভয়েস, ওয়েক ওয়ার্ড)
echo   [3] ট্রে মোড (সিস্টেম ট্রে + ভয়েস)
echo.

set /p MODE="আপনার পছন্দ (1/2/3): "

if "%MODE%"=="1" (
    echo.
    echo ইন্টারেক্টিভ মোড চালু হচ্ছে...
    echo.
    python bro_assistant.py
) else if "%MODE%"=="2" (
    echo.
    echo লিসেনার মোড চালু হচ্ছে...
    echo "ব্রো" বলুন অ্যাক্টিভেট করতে
    echo.
    python bro_listener.py
) else if "%MODE%"=="3" (
    echo.
    echo ট্রে মোড চালু হচ্ছে...
    echo.
    python bro_tray.py
) else (
    echo অবৈধ পছন্দ
    pause
    exit /b 1
)

pause
