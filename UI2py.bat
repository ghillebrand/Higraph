REM ..\Scripts\activate.bat

call pyside6-uic HelpAbout.ui -o src\Ui_HelpAbout
call pyside6-uic Credits.ui -o src\ui_Credits.py
call pyside6-uic form.ui -o src\ui_form.py

pause