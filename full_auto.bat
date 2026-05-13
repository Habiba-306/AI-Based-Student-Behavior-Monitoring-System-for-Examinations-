@echo off
cd /d "C:\Users\PMYLS\OneDrive - Higher Education Commission\Desktop\habibaa\semesters_files\MyFinalYearProject\FinalYearProject\ExamGuard_Project"
echo 🚀 STARTING FULL AUTO-GIT SYSTEM...
echo 📁 Monitoring all file changes...
echo ⏰ Auto-update every 30 seconds
echo ❌ Press Ctrl+C to stop
echo.

:loop
git pull origin main
git add --all
git commit -m "Auto update: %date% %time%" --no-verify
git push origin main
echo ✅ Updated at %time%
timeout /t 30 /nobreak >nul
goto loop