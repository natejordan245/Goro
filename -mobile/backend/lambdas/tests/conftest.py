"""
Shared fixtures and configurations for Lambda function tests.
"""

import json
import os
import sys
import importlib.util
import pytest
from unittest.mock import MagicMock, patch
import boto3
from moto import mock_dynamodb, mock_lambda
from decimal import Decimal

# Helper to import modules from specific Lambda directories
def import_lambda_module(lambda_dir, module_name="lambda_function"):
    """Import a module from a specific Lambda directory."""
    lambda_path = os.path.join(os.path.dirname(__file__), f"../{lambda_dir}")
    module_path = os.path.join(lambda_path, f"{module_name}.py")
    
    if not os.path.exists(module_path):
        return None
    
    spec = importlib.util.spec_from_file_location(f"{lambda_dir}.{module_name}", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def parse_workout_module():
    """Import the parse-workout Lambda module."""
    # Add the parse-workout directory to sys.path temporarily
    parse_workout_path = os.path.join(os.path.dirname(__file__), "../parse-workout")
    sys.path.insert(0, parse_workout_path)
    
    try:
        module = import_lambda_module("parse-workout")
        return module
    finally:
        # Clean up sys.path after the test
        if parse_workout_path in sys.path:
            sys.path.remove(parse_workout_path)

@pytest.fixture
def submit_workout_module():
    """Import the submit-workout Lambda module."""
    # Add the submit-workout directory to sys.path temporarily
    submit_workout_path = os.path.join(os.path.dirname(__file__), "../submit-workout")
    sys.path.insert(0, submit_workout_path)
    
    try:
        module = import_lambda_module("submit-workout")
        return module
    finally:
        # Clean up sys.path after the test
        if submit_workout_path in sys.path:
            sys.path.remove(submit_workout_path)

@pytest.fixture
def get_workouts_module():
    """Import the get-workouts Lambda module."""
    # Add the get-workouts directory to sys.path temporarily
    get_workouts_path = os.path.join(os.path.dirname(__file__), "../get-workouts")
    sys.path.insert(0, get_workouts_path)
    
    try:
        module = import_lambda_module("get-workouts")
        return module
    finally:
        # Clean up sys.path after the test
        if get_workouts_path in sys.path:
            sys.path.remove(get_workouts_path)

# DynamoDB fixtures
@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for boto3."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for testing."""
    with mock_dynamodb():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        
        # Create workout table with required indexes
        table = dynamodb.create_table(
            TableName="UserWorkouts",
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "workoutId", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "workoutId", "AttributeType": "S"},
                {"AttributeName": "date", "AttributeType": "S"},
                {"AttributeName": "userId_exercise", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "DateIndex",
                    "KeySchema": [
                        {"AttributeName": "userId", "KeyType": "HASH"},
                        {"AttributeName": "date", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                },
                {
                    "IndexName": "ExerciseIndex",
                    "KeySchema": [
                        {"AttributeName": "userId_exercise", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                }
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
        )
        
        yield table

@pytest.fixture
def sample_workout_data():
    """Sample workout data for testing."""
    return {
        "userId": "test-user-123",
        "exercises": [
            {
                "name": "bench press",
                "weight": 135.5,
                "reps": 8,
                "sets": 3
            },
            {
                "name": "squat",
                "weight": 225.0,
                "reps": 5,
                "sets": 5
            }
        ]
    }

@pytest.fixture
def populate_dynamodb(dynamodb_table, sample_workout_data):
    """Populate the DynamoDB table with sample workout data."""
    from datetime import datetime
    import time
    
    user_id = sample_workout_data["userId"]
    timestamp = int(time.time())
    date_string = datetime.now().strftime('%Y-%m-%d')
    
    for i, exercise in enumerate(sample_workout_data["exercises"]):
        workout_id = f"DATE#{date_string}#TIME#{timestamp}#{i}"
        user_id_exercise = f"{user_id}#EXERCISE#{exercise['name']}"
        
        dynamodb_table.put_item(
            Item={
                'userId': user_id,
                'workoutId': workout_id,
                'userId_exercise': user_id_exercise,
                'date': date_string,
                'timestamp': str(timestamp),
                'exercise': exercise['name'],
                'sets': exercise['sets'],
                'reps': exercise['reps'],
                'weight': Decimal(str(exercise['weight']))  # Convert to Decimal
            }
        )
    
    # Add some data from a previous date
    older_date = "2023-08-15"
    older_timestamp = timestamp - 86400 * 30  # 30 days ago
    
    for i, exercise in enumerate(sample_workout_data["exercises"]):
        workout_id = f"DATE#{older_date}#TIME#{older_timestamp}#{i}"
        user_id_exercise = f"{user_id}#EXERCISE#{exercise['name']}"
        
        # Calculate weight with Decimal to avoid float precision issues
        older_weight = Decimal(str(exercise['weight'])) * Decimal('0.9')
        
        dynamodb_table.put_item(
            Item={
                'userId': user_id,
                'workoutId': workout_id,
                'userId_exercise': user_id_exercise,
                'date': older_date,
                'timestamp': str(older_timestamp),
                'exercise': exercise['name'],
                'sets': exercise['sets'],
                'reps': exercise['reps'],
                'weight': older_weight  # Using Decimal
            }
        )

# Lambda fixtures
@pytest.fixture
def mock_lambda_client():
    """Mock Lambda client for testing."""
    with mock_lambda():
        client = boto3.client('lambda', region_name='us-east-1')
        
        # Create mock submit-workout Lambda function
        client.create_function(
            FunctionName='submit-workout',
            Runtime='python3.9',
            Role='role-arn',
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': b'def lambda_handler(event, context): return {"statusCode": 200}'},
            Description='Mock submit-workout function',
        )
        
        yield client

# Bedrock fixtures
@pytest.fixture
def mock_bedrock():
    """Mock Bedrock client for testing LLM services."""
    with patch('boto3.client') as mock_client:
        bedrock_mock = MagicMock()
        mock_client.return_value = bedrock_mock
        
        # Configure the mock response
        mock_response = {
            'body': MagicMock(),
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"exercise": "bench press", "sets": 3, "reps": 8, "weight": 135}'}]
        })
        bedrock_mock.invoke_model.return_value = mock_response
        
        yield bedrock_mock 