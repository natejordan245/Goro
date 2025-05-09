"""
Tests for the submit-workout Lambda function.
"""

import json
import time
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest

# Tests for the submit-workout Lambda function
class TestSubmitWorkout:
    """Test cases for the submit-workout Lambda function."""

    def test_validate_exercise_valid(self, submit_workout_module):
        """Test exercise validation with valid exercise data."""
        exercise = {
            "name": "bench press",
            "weight": 135.5,
            "reps": 8,
            "sets": 3
        }
        is_valid, error = submit_workout_module.validate_exercise(exercise)
        assert is_valid is True
        assert error is None

    def test_validate_exercise_missing_field(self, submit_workout_module):
        """Test exercise validation with missing field."""
        exercise = {
            "name": "bench press",
            "weight": 135.5,
            "sets": 3
            # Missing reps field
        }
        is_valid, error = submit_workout_module.validate_exercise(exercise)
        assert is_valid is False
        assert "Missing required fields" in error

    def test_validate_exercise_invalid_types(self, submit_workout_module):
        """Test exercise validation with invalid types."""
        exercise = {
            "name": "bench press",
            "weight": "135.5",  # String instead of number
            "reps": 8,
            "sets": 3
        }
        is_valid, error = submit_workout_module.validate_exercise(exercise)
        assert is_valid is False
        assert "Weight must be a number" in error

    def test_validate_exercise_negative_values(self, submit_workout_module):
        """Test exercise validation with negative values."""
        exercise = {
            "name": "bench press",
            "weight": 135.5,
            "reps": -8,  # Negative reps
            "sets": 3
        }
        is_valid, error = submit_workout_module.validate_exercise(exercise)
        assert is_valid is False
        assert "Reps must be positive" in error

    def test_lambda_handler_success(self, dynamodb_table, submit_workout_module):
        """Test successful workout submission."""
        # Prepare test event
        event = {
            "body": {
                "userId": "test-user-123",
                "exercises": [
                    {
                        "name": "bench press",
                        "weight": 135.5,
                        "reps": 8,
                        "sets": 3
                    }
                ]
            }
        }

        # Call the handler
        with patch('time.time', return_value=1234567890):
            response = submit_workout_module.lambda_handler(event, None)

        # Verify the response
        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["message"] == "Workout saved successfully"
        assert len(response_body["workoutIds"]) == 1

        # Verify data was saved to DynamoDB
        saved_item = dynamodb_table.get_item(
            Key={
                "userId": "test-user-123",
                "workoutId": response_body["workoutIds"][0]
            }
        ).get("Item")

        assert saved_item is not None
        assert saved_item["exercise"] == "bench press"
        assert float(saved_item["weight"]) == 135.5
        assert saved_item["reps"] == 8
        assert saved_item["sets"] == 3

    def test_lambda_handler_multiple_exercises(self, dynamodb_table, submit_workout_module):
        """Test submission with multiple exercises."""
        # Prepare test event
        event = {
            "body": {
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
        }

        # Call the handler
        response = submit_workout_module.lambda_handler(event, None)

        # Verify the response
        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["message"] == "Workout saved successfully"
        assert len(response_body["workoutIds"]) == 2

    def test_lambda_handler_invalid_exercise(self, submit_workout_module):
        """Test submission with invalid exercise data."""
        # Prepare test event
        event = {
            "body": {
                "userId": "test-user-123",
                "exercises": [
                    {
                        "name": "bench press",
                        "weight": 135.5,
                        "sets": 3
                        # Missing reps
                    }
                ]
            }
        }

        # Call the handler
        response = submit_workout_module.lambda_handler(event, None)

        # Verify the response
        assert response["statusCode"] == 400
        response_body = json.loads(response["body"])
        assert "Invalid exercise" in response_body["error"]

    def test_lambda_handler_missing_user_id(self, submit_workout_module):
        """Test submission with missing userId."""
        # Prepare test event
        event = {
            "body": {
                # Missing userId
                "exercises": [
                    {
                        "name": "bench press",
                        "weight": 135.5,
                        "reps": 8,
                        "sets": 3
                    }
                ]
            }
        }

        # Call the handler
        response = submit_workout_module.lambda_handler(event, None)

        # Verify the response
        assert response["statusCode"] == 400
        response_body = json.loads(response["body"])
        assert "userId is required" in response_body["error"]

    def test_lambda_handler_empty_exercises(self, submit_workout_module):
        """Test submission with empty exercises array."""
        # Prepare test event
        event = {
            "body": {
                "userId": "test-user-123",
                "exercises": []
            }
        }

        # Call the handler
        response = submit_workout_module.lambda_handler(event, None)

        # Verify the response
        assert response["statusCode"] == 400
        response_body = json.loads(response["body"])
        assert "exercises must be a non-empty array" in response_body["error"]

    def test_lambda_handler_string_body(self, dynamodb_table, submit_workout_module):
        """Test handling of string body in the event."""
        # Prepare test event
        event = {
            "body": json.dumps({
                "userId": "test-user-123",
                "exercises": [
                    {
                        "name": "bench press",
                        "weight": 135.5,
                        "reps": 8,
                        "sets": 3
                    }
                ]
            })
        }

        # Call the handler
        response = submit_workout_module.lambda_handler(event, None)

        # Verify the response
        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["message"] == "Workout saved successfully"

    def test_lambda_handler_invalid_json(self, submit_workout_module):
        """Test handling of invalid JSON in the body."""
        # Prepare test event
        event = {
            "body": "this is not valid JSON"
        }

        # Call the handler
        response = submit_workout_module.lambda_handler(event, None)

        # Verify the response
        assert response["statusCode"] == 400
        response_body = json.loads(response["body"])
        assert "Invalid JSON" in response_body["error"] 