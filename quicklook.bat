ECHO off

SET where=C:\Windows\System32\where.exe
SET anaconda_config=%~dp0%anaconda_dir.txt

:: create anaconda_config file if it doesn't exist
IF NOT EXIST %anaconda_config% (
	ECHO "Quick Look doesn't know where your Anaconda directory is yet."
	ECHO "Locating Anaconda directory...
	ECHO "(result will be stored in anaconda_dir.txt for future use)"
	for /f "delims=_ tokens=1" %%a in ('%where% /r %userprofile% _conda.exe') do ECHO %%a >anaconda_dir.txt
) 

:: read anaconda dir from anaconda_config file
for /f "delims= " %%x in (%anaconda_config%) do set anaconda_dir=%%x
SET conda=%anaconda_dir%condabin\conda.bat
SET env_dir=%anaconda_dir%envs
SET quicklook_env_name=quicklook

:: activate LiProd conda environment (create conda environment if it doesn't exist)
ECHO "activating Quick Look conda environment..."
CALL %conda% activate %quicklook_env_name%
IF %ERRORLEVEL% == 0 (
	%env_dir%\%quicklook_env_name%\python.exe %~dp0%quicklook.py
) ELSE (
	ECHO "Oh nooo, a valid Quick-Look environment doesn't exist.  Let's create one..."
	%conda% create --prefix %env_dir%\%quicklook_env_name% --file %~dp0%quicklook.env

	ECHO "There, you've now got a Quick Look environment. (You won't have to do this part again...for this particular version)"
	ECHO "activating environment..."
	%conda% activate %quicklook_env_name%
	%env_dir%\%quicklook_env_name%\python.exe %~dp0%quicklook.py
)

cmd /k
