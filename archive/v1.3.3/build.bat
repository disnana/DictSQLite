@echo off
E:
cd "E:\data-backup\code\Pycharmプロジェクト用フォルダ\New Disnana\dict sqlite manager プロジェクト\v1.3.2"
python remove.py
python setup.py sdist
python setup.py bdist_wheel