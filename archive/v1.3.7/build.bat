@echo off
E:
cd %~dp0
python remove.py
python setup.py sdist
python setup.py bdist_wheel