@echo off
C:
cd C:\Program Files\Python312\Lib\site-packages\twine
echo �A�b�v���[�h����f�B���N�g�����m�F���Ă�������
echo "%~dp0dist\*"
pause
__main__.py upload --repository pypi "%~dp0dist\*" --verbose
pause