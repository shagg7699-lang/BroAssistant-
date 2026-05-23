@echo off
chcp 65001 >nul
title ব্রো (Bro) — সেটআপ v3.0

echo ╔═══════════════════════════════════════════╗
echo ║     ব্রো (Bro) v3.0 — সেটআপ উইজার্ড       ║
echo ╚═══════════════════════════════════════════╝
echo.

:: Python চেক
echo [1/5] Python চেক করা হচ্ছে...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python পাওয়া যায়নি!
    echo    https://www.python.org/downloads/ থেকে Python 3.10+ ইনস্টল করুন
    pause
    exit /b 1
)
echo ✓ Python পাওয়া গেছে
echo.

:: ভার্চুয়াল এনভায়রনমেন্ট
echo [2/5] ভার্চুয়াল এনভায়রনমেন্ট তৈরি হচ্ছে...
if not exist ".venv" (
    python -m venv .venv
    echo ✓ .venv তৈরি হয়েছে
) else (
    echo ✓ .venv ইতিমধ্যে আছে
)
call .venv\Scripts\activate.bat
echo.

:: ডিপেন্ডেন্সি ইনস্টল
echo [3/5] ডিপেন্ডেন্সি ইনস্টল হচ্ছে...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo.

:: .env চেক
echo [4/5] .env ফাইল চেক করা হচ্ছে...
if not exist ".env" (
    echo ⚠ .env ফাইল নেই!
    echo   .env.example থেকে .env তৈরি করুন এবং API কী যোগ করুন
    copy .env.example .env >nul 2>&1
    echo ✓ .env.example থেকে .env কপি করা হয়েছে — API কী যোগ করুন
) else (
    echo ✓ .env ফাইল পাওয়া গেছে
)
echo.

:: ডাটা ফোল্ডার
echo [5/5] ডাটা ফোল্ডার তৈরি হচ্ছে...
if not exist "data" mkdir data
if not exist "data\logs" mkdir data\logs
if not exist "data\plugins" mkdir data\plugins
if not exist "data\video_output" mkdir data\video_output
echo ✓ ডাটা ফোল্ডার প্রস্তুত
echo.

echo ╔═══════════════════════════════════════════╗
echo ║         ✓ সেটআপ সম্পন্ন!                   ║
echo ║                                           ║
echo ║   এখন Run_Bro.bat চালান                   ║
echo ║   অথবা: python bro_assistant.py           ║
echo ╚═══════════════════════════════════════════╝
echo.
pause
