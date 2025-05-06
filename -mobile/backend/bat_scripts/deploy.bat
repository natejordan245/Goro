@echo off
echo ===== Starting Lambda Deployment =====

:: Create clean deployment packages (ONLY lambda_function.py)
echo Creating clean packages...

:: Package submit-workout
powershell -Command "Compress-Archive -Path ..\lambdas\submit-workout\lambda_function.py -DestinationPath submit-workout.zip -Force"

:: Package get-workouts
powershell -Command "Compress-Archive -Path ..\lambdas\get-workouts\lambda_function.py -DestinationPath get-workouts.zip -Force"

:: Package parse-workout
powershell -Command "Compress-Archive -Path ..\lambdas\parse-workout\lambda_function.py -DestinationPath parse-workout.zip -Force"

:: Deploy to AWS
echo.
echo ===== Deploying to AWS =====
aws lambda update-function-code --function-name submit-workout --zip-file fileb://submit-workout.zip
aws lambda update-function-code --function-name get-workouts --zip-file fileb://get-workouts.zip
aws lambda update-function-code --function-name parse-workout --zip-file fileb://parse-workout.zip

:: Cleanup
echo.
echo ===== Cleaning up =====
del submit-workout.zip
del get-workouts.zip
del parse-workout.zip

echo.
echo ===== Deployment Complete =====
pause