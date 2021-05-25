@echo off
call C:\ProgramData\Anaconda3\Scripts\activate.bat
cd /D C:\Users\DXX0511A\Desktop\MiR_dashboard
echo %cd%
streamlit run app.py