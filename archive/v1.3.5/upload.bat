@echo off
C:
cd C:\Program Files\Python312\Lib\site-packages\twine
echo アップロードするディレクトリを確認してください
echo "%~dp0dist\*"
pause
__main__.py upload --repository pypi "%~dp0dist\*" --verbose
pause