@echo off
REM Lambda Test Runner Script
REM This script runs the pytest suite for all Lambda functions
REM
REM Usage: run_tests.bat [--lambda=NAME]
REM Options:
REM   --lambda=NAME   Test only a specific Lambda function (parse-workout, submit-workout, get-workouts)

echo Running tests for Lambda functions...
echo.

cd %~dp0\..

REM Check if we're testing a specific Lambda
set LAMBDA_ARG=
set LAMBDA_NAME=

for %%a in (%*) do (
  echo %%a | findstr /r "\-\-lambda=" > nul && (
    set LAMBDA_ARG=%%a
    for /f "tokens=2 delims==" %%b in ("%%a") do set LAMBDA_NAME=%%b
  )
)

if defined LAMBDA_NAME (
  echo Testing only the %LAMBDA_NAME% Lambda function
)

REM Run the tests
python -m pytest tests -v %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Some tests failed! See report above.
) else (
    echo.
    echo All tests passed successfully!
)

echo.
echo Remember to install the required packages if not already installed:
echo pip install pytest moto boto3 coverage pytest-mock

pause 