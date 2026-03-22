@echo off
echo [1/3] Bazalarni tozalash...
del /f /q .github\workflows\*.db 2>nul
echo [2/3] Kodlarni tayyorlash...
git add .
git commit -m "Final link fix and UI update"
echo [3/3] Internetga yuborish...
git push -f
echo -----------------------------------
echo HAMMASI TAYYOR! 
echo Endi botga kirib /start bosing.
echo -----------------------------------
pause
