"""
Tests for the get-workouts Lambda function.
"""

import json
from unittest.mock import patch, MagicMock
from decimal import Decimal

import pytest
import boto3


class TestDecimalEncoder:
    """Test cases for the DecimalEncoder class."""

    def test_encode_decimal(self, get_workouts_module):
        """Test encoding Decimal values to float."""
        encoder = get_workouts_module.DecimalEncoder()
        result = encoder.default(Decimal('12.345'))
        assert result == 12.345
        assert isinstance(result, float)

    def test_encode_other_types(self, get_workouts_module):
        """Test encoder falls back to default for non-Decimal types."""
        encoder = get_workouts_module.DecimalEncoder()
        with pytest.raises(TypeError):
            encoder.default("not a decimal")


class TestWorkoutRepository:
    """Test cases for the WorkoutRepository class."""

    def test_get_workouts_by_date(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test retrieving workouts by date."""
        # Setup
        from datetime import datetime
        user_id = sample_workout_data["userId"]
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Execute
        repo = get_workouts_module.WorkoutRepository(table_name='UserWorkouts')
        result = repo.get_workouts_by_date(user_id, date)
        
        # Verify
        assert result['success'] is True
        assert result['date'] == date
        assert len(result['workouts']) == 2  # Two exercises from sample data
        assert result['workouts'][0]['exercise'] in ['bench press', 'squat']

    def test_get_workouts_by_exercise(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test retrieving workouts by exercise."""
        # Setup
        user_id = sample_workout_data["userId"]
        exercise = "bench press"
        
        # Execute
        repo = get_workouts_module.WorkoutRepository(table_name='UserWorkouts')
        result = repo.get_workouts_by_exercise(user_id, exercise)
        
        # Verify
        assert result['success'] is True
        assert result['exercise'] == exercise
        assert len(result['workouts']) == 2  # Current and past workout from sample data
        assert all(workout['exercise'] == exercise for workout in result['workouts'])
        
    def test_get_all_user_workouts(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test retrieving all workouts for a user."""
        # Setup
        user_id = sample_workout_data["userId"]
        
        # Execute
        repo = get_workouts_module.WorkoutRepository(table_name='UserWorkouts')
        result = repo.get_all_user_workouts(user_id)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert len(result['workouts']) == 4  # 2 exercises * 2 dates
        
    def test_repository_error_handling(self, get_workouts_module):
        """Test error handling in the repository."""
        # Create repository with non-existent table
        repo = get_workouts_module.WorkoutRepository(table_name='NonExistentTable')
        
        # Exercise functions and check error handling
        date_result = repo.get_workouts_by_date('user1', '2023-01-01')
        assert date_result['success'] is False
        assert 'error' in date_result
        
        exercise_result = repo.get_workouts_by_exercise('user1', 'squat')
        assert exercise_result['success'] is False
        assert 'error' in exercise_result
        
        all_result = repo.get_all_user_workouts('user1')
        assert all_result['success'] is False
        assert 'error' in all_result


class TestWorkoutService:
    """Test cases for the WorkoutService class."""

    def test_get_workout_summary(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test generating a workout summary grouped by date."""
        # Setup
        user_id = sample_workout_data["userId"]
        
        # Execute
        service = get_workouts_module.WorkoutService()
        result = service.get_workout_summary(user_id)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert 'workout_summary' in result
        assert len(result['workout_summary']) == 2  # Two dates in sample data
        
        # Verify dates are in descending order (newest first)
        dates = [day['date'] for day in result['workout_summary']]
        assert dates[0] > dates[1]
        
    def test_get_date_workouts(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test getting workouts for a specific date."""
        # Setup
        from datetime import datetime
        user_id = sample_workout_data["userId"]
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Execute
        service = get_workouts_module.WorkoutService()
        result = service.get_date_workouts(user_id, date)
        
        # Verify
        assert result['success'] is True
        assert result['date'] == date
        assert len(result['workouts']) == 2
        
    def test_get_exercise_workouts(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test getting all instances of a specific exercise."""
        # Setup
        user_id = sample_workout_data["userId"]
        exercise = "squat"
        
        # Execute
        service = get_workouts_module.WorkoutService()
        result = service.get_exercise_workouts(user_id, exercise)
        
        # Verify
        assert result['success'] is True
        assert result['exercise'] == exercise
        assert len(result['workouts']) == 2  # From two different dates
        assert all(workout['exercise'] == exercise for workout in result['workouts'])
        
    def test_get_exercise_progress(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test getting progress data for an exercise."""
        # Setup
        user_id = sample_workout_data["userId"]
        exercise = "bench press"
        
        # Execute
        service = get_workouts_module.WorkoutService()
        result = service.get_exercise_progress(user_id, exercise)
        
        # Verify
        assert result['success'] is True
        assert result['exercise'] == exercise
        assert 'progress_data' in result
        assert len(result['progress_data']) == 2  # Two dates with this exercise
        assert 'max_weight' in result
        assert 'max_weight_date' in result
        
        # Verify progress data format
        for entry in result['progress_data']:
            assert 'date' in entry
            assert 'weight' in entry
            assert 'reps' in entry
            assert 'sets' in entry
            assert 'volume' in entry
            
    def test_get_exercise_progress_no_data(self, get_workouts_module, dynamodb_table):
        """Test handling of exercise with no data."""
        # Execute
        service = get_workouts_module.WorkoutService()
        result = service.get_exercise_progress('user1', 'nonexistent')
        
        # Verify
        assert result['success'] is False
        assert 'error' in result
        assert 'No data found' in result['error']


class TestRequestHandler:
    """Test cases for the RequestHandler class."""

    def test_extract_parameters(self, get_workouts_module):
        """Test extracting parameters from different event formats."""
        # Setup
        handler = get_workouts_module.RequestHandler()
        
        # Test with parameters in body
        event1 = {
            "body": {
                "userId": "user1",
                "query_type": "date",
                "date": "2023-01-01",
                "exercise": "squat"
            }
        }
        params1 = handler.extract_parameters(event1)
        assert params1['user_id'] == "user1"
        assert params1['query_type'] == "date"
        assert params1['date'] == "2023-01-01"
        assert params1['exercise'] == "squat"
        
        # Test with string body
        event2 = {
            "body": json.dumps({
                "userId": "user2",
                "queryType": "exercise",
                "exercise": "bench press"
            })
        }
        params2 = handler.extract_parameters(event2)
        assert params2['user_id'] == "user2"
        assert params2['query_type'] == "exercise"
        assert params2['exercise'] == "bench press"
        
        # Test with query parameters
        event3 = {
            "queryStringParameters": {
                "userId": "user3",
                "query_type": "progress",
                "exercise": "deadlift"
            }
        }
        params3 = handler.extract_parameters(event3)
        assert params3['user_id'] == "user3"
        assert params3['query_type'] == "progress"
        assert params3['exercise'] == "deadlift"
        
    def test_route_query(self, get_workouts_module):
        """Test routing to the appropriate service method based on query type."""
        # Setup
        handler = get_workouts_module.RequestHandler()
        
        # Create mock workout service
        mock_service = MagicMock()
        mock_service.get_date_workouts.return_value = {"success": True, "test": "date"}
        mock_service.get_exercise_workouts.return_value = {"success": True, "test": "exercise"}
        mock_service.get_exercise_progress.return_value = {"success": True, "test": "progress"}
        mock_service.get_workout_summary.return_value = {"success": True, "test": "summary"}
        
        handler.workout_service = mock_service
        
        # Test routing for different query types
        date_result = handler._route_query({
            "user_id": "user1", 
            "query_type": "date", 
            "date": "2023-01-01"
        })
        assert date_result["test"] == "date"
        mock_service.get_date_workouts.assert_called_with("user1", "2023-01-01")
        
        exercise_result = handler._route_query({
            "user_id": "user1", 
            "query_type": "exercise", 
            "exercise": "squat"
        })
        assert exercise_result["test"] == "exercise"
        mock_service.get_exercise_workouts.assert_called_with("user1", "squat")
        
        progress_result = handler._route_query({
            "user_id": "user1", 
            "query_type": "progress", 
            "exercise": "bench"
        })
        assert progress_result["test"] == "progress"
        mock_service.get_exercise_progress.assert_called_with("user1", "bench")
        
        summary_result = handler._route_query({
            "user_id": "user1", 
            "query_type": "summary"
        })
        assert summary_result["test"] == "summary"
        mock_service.get_workout_summary.assert_called_with("user1")
        
    def test_format_response(self, get_workouts_module):
        """Test formatting results into proper HTTP responses."""
        # Setup
        handler = get_workouts_module.RequestHandler()
        
        # Test successful response
        success_result = {
            "success": True,
            "user_id": "user1",
            "data": {"test": "value"}
        }
        success_response = handler._format_response(success_result)
        assert success_response["statusCode"] == 200
        assert "success" not in json.loads(success_response["body"])
        
        # Test error response
        error_result = {
            "success": False,
            "error": "Test error message"
        }
        error_response = handler._format_response(error_result)
        assert error_response["statusCode"] == 500
        assert "error" in json.loads(error_response["body"])
        
    def test_error_response(self, get_workouts_module):
        """Test creating error responses with different status codes."""
        # Setup
        handler = get_workouts_module.RequestHandler()
        
        # Test different status codes
        error_400 = handler._error_response(400, "Bad Request")
        assert error_400["statusCode"] == 400
        assert json.loads(error_400["body"])["error"] == "Bad Request"
        
        error_500 = handler._error_response(500, "Server Error")
        assert error_500["statusCode"] == 500
        assert json.loads(error_500["body"])["error"] == "Server Error"


class TestLambdaHandler:
    """Test cases for the Lambda handler function."""

    def test_lambda_handler_success(self, get_workouts_module, dynamodb_table, populate_dynamodb, sample_workout_data):
        """Test successful Lambda execution with different query types."""
        # Setup
        user_id = sample_workout_data["userId"]
        
        # Test summary query (default)
        summary_event = {
            "body": {
                "userId": user_id
            }
        }
        summary_response = get_workouts_module.lambda_handler(summary_event, None)
        assert summary_response["statusCode"] == 200
        summary_body = json.loads(summary_response["body"])
        assert "workout_summary" in summary_body
        
        # Test date query
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
        date_event = {
            "body": {
                "userId": user_id,
                "query_type": "date",
                "date": date
            }
        }
        date_response = get_workouts_module.lambda_handler(date_event, None)
        assert date_response["statusCode"] == 200
        date_body = json.loads(date_response["body"])
        assert "date" in date_body
        assert "workouts" in date_body
        
        # Test exercise query
        exercise_event = {
            "body": {
                "userId": user_id,
                "query_type": "exercise",
                "exercise": "bench press"
            }
        }
        exercise_response = get_workouts_module.lambda_handler(exercise_event, None)
        assert exercise_response["statusCode"] == 200
        exercise_body = json.loads(exercise_response["body"])
        assert "exercise" in exercise_body
        assert "workouts" in exercise_body
        
        # Test progress query
        progress_event = {
            "body": {
                "userId": user_id,
                "query_type": "progress",
                "exercise": "bench press"
            }
        }
        progress_response = get_workouts_module.lambda_handler(progress_event, None)
        assert progress_response["statusCode"] == 200
        progress_body = json.loads(progress_response["body"])
        assert "exercise" in progress_body
        assert "progress_data" in progress_body
        
    def test_lambda_handler_missing_user_id(self, get_workouts_module):
        """Test Lambda execution with missing userId."""
        # Setup
        event = {
            "body": {
                "query_type": "summary"
                # Missing userId
            }
        }
        
        # Execute
        response = get_workouts_module.lambda_handler(event, None)
        
        # Verify
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "user_id is required" in body["error"]
        
    def test_lambda_handler_invalid_json(self, get_workouts_module):
        """Test Lambda execution with invalid JSON in body."""
        # Setup
        event = {
            "body": "this is not valid JSON"
        }
        
        # Execute
        response = get_workouts_module.lambda_handler(event, None)
        
        # Verify
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "Invalid JSON" in body["error"] 