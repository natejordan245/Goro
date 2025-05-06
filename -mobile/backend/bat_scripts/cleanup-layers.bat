@echo off
echo ===== Cleaning up old layer versions =====

:: Loop through versions 1 to 6 and delete them
for /l %%v in (1,1,6) do (
    echo Deleting version %%v
    aws lambda delete-layer-version --layer-name workout-dependencies --version-number %%v
)

echo.
echo ===== Cleanup Complete =====
echo Only version 7 remains
pause
