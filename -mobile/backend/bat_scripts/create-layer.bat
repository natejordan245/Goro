@echo off
echo ===== Creating Lambda Layer =====

:: Get current layer versions and delete them
echo Cleaning up old layer versions...
aws lambda list-layer-versions --layer-name workout-dependencies --query "LayerVersions[*].Version" --output text > versions.txt
for /f "tokens=*" %%a in (versions.txt) do (
    echo Deleting version %%a
    aws lambda delete-layer-version --layer-name workout-dependencies --version-number %%a
)
del versions.txt

:: Create fresh directories
echo Creating directories...
if exist layer-demo rmdir /s /q layer-demo
mkdir layer-demo
cd layer-demo
mkdir python

:: Install dependencies to layer
echo.
echo Installing dependencies to layer...
pip install boto3==1.34.29 -t python

:: Create layer zip
echo.
echo Creating layer zip...
powershell Compress-Archive -Path python -DestinationPath layer.zip -Force

:: Upload layer to AWS
echo.
echo Uploading layer to AWS...
aws lambda publish-layer-version --layer-name workout-dependencies --description "Dependencies for workout functions" --compatible-runtimes python3.13 --zip-file fileb://layer.zip > layer-response.json

:: Get the Layer ARN from the response
echo.
echo Getting Layer ARN...
for /f "tokens=2 delims=:" %%a in ('findstr "LayerVersionArn" layer-response.json') do set LAYER_ARN=%%a
set LAYER_ARN=%LAYER_ARN:"=%
set LAYER_ARN=%LAYER_ARN:,=%
set LAYER_ARN=%LAYER_ARN: =%

:: Echo the ARN to verify we got it
echo Layer ARN: %LAYER_ARN%

:: Update ALL Lambda functions to use the layer
echo.
echo Updating Lambda functions to use layer...
aws lambda update-function-configuration --function-name submit-workout --layers "%LAYER_ARN%"
echo Updated submit-workout
aws lambda update-function-configuration --function-name get-workouts --layers "%LAYER_ARN%"
echo Updated get-workouts
aws lambda update-function-configuration --function-name parse-workout --layers "%LAYER_ARN%"
echo Updated parse-workout

:: Create clean deployment packages (just lambda_function.py)
echo.
echo Creating clean deployment packages...
cd ..

:: Clean packages (only lambda_function.py)
powershell Compress-Archive -Path ..\lambdas\submit-workout\lambda_function.py -DestinationPath submit-workout.zip -Force
powershell Compress-Archive -Path ..\lambdas\get-workouts\lambda_function.py -DestinationPath get-workouts.zip -Force
powershell Compress-Archive -Path ..\lambdas\parse-workout\lambda_function.py -DestinationPath parse-workout.zip -Force

:: Deploy clean code to AWS
echo.
echo Deploying clean code to AWS...
aws lambda update-function-code --function-name submit-workout --zip-file fileb://submit-workout.zip
aws lambda update-function-code --function-name get-workouts --zip-file fileb://get-workouts.zip
aws lambda update-function-code --function-name parse-workout --zip-file fileb://parse-workout.zip

:: Cleanup
echo.
echo Cleaning up temporary files...
rmdir /s /q layer-demo
del submit-workout.zip
del get-workouts.zip
del parse-workout.zip

echo.
echo ===== Layer Creation and Deployment Complete =====
echo Your Lambda functions are now using the shared layer for dependencies
pause
