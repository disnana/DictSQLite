@echo off
C:
cd C:\Program Files\Python312\Lib\site-packages\twine
echo テストするディレクトリを確認してください
echo "%~dp0dist\*"
pause
__main__.py check "%~dp0dist\*"
pause