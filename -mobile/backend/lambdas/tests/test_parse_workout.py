"""
Tests for the parse-workout Lambda function.
"""

import json
from unittest.mock import patch, MagicMock, ANY

import pytest
import boto3


class TestWorkoutData:
    """Test cases for the WorkoutData class."""

    def test_initialization(self, parse_workout_module):
        """Test initialization with and without data."""
        # Test with no data
        workout1 = parse_workout_module.WorkoutData()
        assert workout1.data == {}
        assert workout1.missing_fields == []

        # Test with data
        workout_data = {
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        }
        workout2 = parse_workout_module.WorkoutData(workout_data)
        assert workout2.data == workout_data
        assert workout2.missing_fields == []

    def test_to_dict(self, parse_workout_module):
        """Test converting to dictionary."""
        workout_data = {
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        }
        workout = parse_workout_module.WorkoutData(workout_data)
        result = workout.to_dict()
        assert result == workout_data
        # Ensure returned dict is a copy
        result["exercise"] = "squat"
        assert workout.data["exercise"] == "bench press"

    def test_to_submit_format(self, parse_workout_module):
        """Test converting to submit-workout format."""
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        })
        result = workout.to_submit_format()
        assert result == {
            "name": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        }

        # Test with missing fields
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            # Missing fields
        })
        result = workout.to_submit_format()
        assert result["name"] == "bench press"
        assert result["weight"] == 0
        assert result["reps"] == 0
        assert result["sets"] == 0

    def test_normalize(self, parse_workout_module):
        """Test normalizing numeric fields."""
        # Test conversion to proper types
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": "135.5",  # String weight
            "reps": "8",       # String reps
            "sets": "3"        # String sets
        })
        workout.normalize()
        assert workout.data["weight"] == 135.5
        assert isinstance(workout.data["weight"], float)
        assert workout.data["reps"] == 8
        assert isinstance(workout.data["reps"], int)
        assert workout.data["sets"] == 3
        assert isinstance(workout.data["sets"], int)

        # Test handling of invalid values
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": "invalid",
            "reps": None,
            "sets": {}
        })
        workout.normalize()
        assert workout.data["weight"] is None
        assert workout.data["reps"] is None
        assert workout.data["sets"] is None

    def test_standardize_exercise_name(self, parse_workout_module):
        """Test standardizing exercise names to lowercase."""
        # Test lowercase conversion
        workout = parse_workout_module.WorkoutData({
            "exercise": "Bench Press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        })
        workout.standardize_exercise_name()
        assert workout.data["exercise"] == "bench press"

        # Test handling of missing exercise
        workout = parse_workout_module.WorkoutData({
            "weight": 135,
            "reps": 8,
            "sets": 3
        })
        workout.standardize_exercise_name()
        assert "exercise" not in workout.data

    def test_validate(self, parse_workout_module):
        """Test validation of workout data."""
        # Test valid data
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        })
        is_valid = workout.validate()
        assert is_valid is True
        assert workout.missing_fields == []

        # Test missing fields
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 135,
            # Missing reps and sets
        })
        is_valid = workout.validate()
        assert is_valid is False
        assert "reps" in workout.missing_fields
        assert "sets" in workout.missing_fields

        # Test invalid values
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 0,  # Valid - bodyweight exercise
            "reps": 0,    # Invalid - must be > 0
            "sets": 0     # Invalid - must be > 0
        })
        is_valid = workout.validate()
        assert is_valid is False
        assert "reps" in workout.missing_fields
        assert "sets" in workout.missing_fields
        assert "weight" not in workout.missing_fields  # weight can be 0

        # Test invalid structure
        workout = parse_workout_module.WorkoutData("not a dictionary")
        is_valid = workout.validate()
        assert is_valid is False
        assert len(workout.missing_fields) > 0

    def test_merge_with(self, parse_workout_module):
        """Test merging with another WorkoutData object."""
        # Setup
        workout1 = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 135,
            # Missing reps and sets
        })
        workout2 = parse_workout_module.WorkoutData({
            "exercise": "squat",  # Different exercise
            "weight": 225,
            "reps": 5,
            "sets": 5
        })

        # Execute
        workout1.merge_with(workout2)

        # Verify - only missing fields should be filled in
        assert workout1.data["exercise"] == "bench press"  # Original value preserved
        assert workout1.data["weight"] == 135             # Original value preserved
        assert workout1.data["reps"] == 5                 # Filled in from workout2
        assert workout1.data["sets"] == 5                 # Filled in from workout2


class TestLLMService:
    """Test cases for the LLMService class."""

    def test_build_context(self, parse_workout_module):
        """Test building context from chat history."""
        service = parse_workout_module.LLMService()
        
        # Test with empty history
        empty_result = service._build_context([])
        assert empty_result == ""
        
        # Test with single message
        history1 = [{"role": "user", "content": "I did bench press today"}]
        result1 = service._build_context(history1)
        assert "User: I did bench press today" in result1
        
        # Test with multiple messages
        history2 = [
            {"role": "user", "content": "I did bench press today"},
            {"role": "assistant", "content": "Great! How many sets and reps?"},
            {"role": "user", "content": "3 sets of 8 reps with 135 lbs"}
        ]
        result2 = service._build_context(history2)
        assert "User: I did bench press today" in result2
        assert "Assistant: Great! How many sets and reps?" in result2
        assert "User: 3 sets of 8 reps with 135 lbs" in result2

    def test_build_prompt(self, parse_workout_module):
        """Test building prompt for the LLM."""
        service = parse_workout_module.LLMService()
        
        # Test with message only
        message = "I did bench press 3x8 at 135 lbs"
        prompt1 = service._build_prompt(message, "")
        assert "Extract workout information" in prompt1
        assert "Current message: I did bench press" in prompt1
        assert "JSON" in prompt1
        assert "exercise" in prompt1
        assert "sets" in prompt1
        assert "reps" in prompt1
        assert "weight" in prompt1
        assert "lowercase" in prompt1.lower()
        
        # Test with context
        context = "User: I'm planning my workout\nAssistant: What are you planning?"
        prompt2 = service._build_prompt(message, context)
        assert "Previous context:" in prompt2
        assert "I'm planning my workout" in prompt2

    def test_parse_json_from_response(self, parse_workout_module):
        """Test extracting JSON from LLM response text."""
        service = parse_workout_module.LLMService()
        
        # Test valid JSON response
        response1 = '{"exercise": "bench press", "sets": 3, "reps": 8, "weight": 135}'
        result1 = service._parse_json_from_response(response1)
        assert result1["exercise"] == "bench press"
        assert result1["sets"] == 3
        assert result1["reps"] == 8
        assert result1["weight"] == 135
        
        # Test JSON with text before/after
        response2 = 'Here is the workout data: {"exercise": "squat", "sets": 5, "reps": 5, "weight": 225} Hope that helps!'
        result2 = service._parse_json_from_response(response2)
        assert result2["exercise"] == "squat"
        
        # Test forcing lowercase for exercise
        response3 = '{"exercise": "Bench Press", "sets": 3, "reps": 8, "weight": 135}'
        result3 = service._parse_json_from_response(response3)
        assert result3["exercise"] == "bench press"
        
        # Test invalid response
        response4 = 'No JSON here'
        result4 = service._parse_json_from_response(response4)
        assert result4 is None
        
        # Test malformed JSON
        response5 = '{"exercise": "bench press", "sets": 3, "reps": 8, "weight": 135'  # Missing closing brace
        result5 = service._parse_json_from_response(response5)
        assert result5 is None

    @patch('boto3.client')
    def test_extract_workout(self, mock_boto3, parse_workout_module):
        """Test extracting workout data from user message."""
        # Setup mock response
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"exercise": "bench press", "sets": 3, "reps": 8, "weight": 135}'}]
        })
        mock_bedrock.invoke_model.return_value = mock_response
        
        # Execute
        service = parse_workout_module.LLMService()
        result = service.extract_workout("I did bench press 3x8 at 135 lbs", [])
        
        # Verify
        assert result["exercise"] == "bench press"
        assert result["sets"] == 3
        assert result["reps"] == 8
        assert result["weight"] == 135
        
        # Verify Bedrock was called with appropriate parameters
        mock_bedrock.invoke_model.assert_called_once()
        call_args = mock_bedrock.invoke_model.call_args[1]
        assert call_args["modelId"] == "anthropic.claude-instant-v1"
        assert "anthropic_version" in json.loads(call_args["body"])
        assert "messages" in json.loads(call_args["body"])
        
    @patch('boto3.client')
    def test_extract_workout_error_handling(self, mock_boto3, parse_workout_module):
        """Test error handling in workout extraction."""
        # Setup mock to raise exception
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock
        mock_bedrock.invoke_model.side_effect = boto3.exceptions.Boto3Error("Test error")
        
        # Execute
        service = parse_workout_module.LLMService()
        result = service.extract_workout("I did bench press 3x8 at 135 lbs", [])
        
        # Verify error is handled gracefully
        assert result is None

    def test_get_model_info(self, parse_workout_module):
        """Test getting model information."""
        # Test with default model
        service1 = parse_workout_module.LLMService()
        info1 = service1.get_model_info()
        assert info1["model_id"] == "anthropic.claude-instant-v1"
        assert info1["service"] == "AWS Bedrock"
        assert info1["provider"] == "Anthropic"
        
        # Test with custom model
        service2 = parse_workout_module.LLMService(model_id="custom.model")
        info2 = service2.get_model_info()
        assert info2["model_id"] == "custom.model"
        assert info2["provider"] == "Unknown"


class TestWorkoutSubmissionService:
    """Test cases for the WorkoutSubmissionService class."""

    @patch('boto3.client')
    def test_submit_workout_success(self, mock_boto3, parse_workout_module):
        """Test successful workout submission."""
        # Setup mock Lambda client
        mock_lambda = MagicMock()
        mock_boto3.return_value = mock_lambda
        
        # Configure success response
        mock_response = {
            'StatusCode': 200,
            'Payload': MagicMock()
        }
        mock_response['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Workout saved successfully',
                'workoutIds': ['test-workout-id'],
                'date': '2023-01-01',
                'count': 1
            })
        }).encode()
        mock_lambda.invoke.return_value = mock_response
        
        # Execute
        service = parse_workout_module.WorkoutSubmissionService()
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        })
        success, workout_id = service.submit_workout(workout, "test-user")
        
        # Verify
        assert success is True
        assert workout_id == "test-workout-id"
        
        # Verify Lambda was invoked correctly
        mock_lambda.invoke.assert_called_once()
        call_args = mock_lambda.invoke.call_args[1]
        assert call_args["FunctionName"] == "submit-workout"
        payload = json.loads(call_args["Payload"])
        assert payload["body"]["userId"] == "test-user"
        assert len(payload["body"]["exercises"]) == 1
        assert payload["body"]["exercises"][0]["name"] == "bench press"

    @patch('boto3.client')
    def test_submit_workout_error(self, mock_boto3, parse_workout_module):
        """Test error handling in workout submission."""
        # Setup mock Lambda client
        mock_lambda = MagicMock()
        mock_boto3.return_value = mock_lambda
        
        # Configure error response
        mock_response = {
            'StatusCode': 200,  # Lambda invocation succeeded but function returned error
            'Payload': MagicMock()
        }
        mock_response['Payload'].read.return_value = json.dumps({
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid exercise data'
            })
        }).encode()
        mock_lambda.invoke.return_value = mock_response
        
        # Execute
        service = parse_workout_module.WorkoutSubmissionService()
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        })
        success, workout_id = service.submit_workout(workout, "test-user")
        
        # Verify
        assert success is False
        assert workout_id is None

    @patch('boto3.client')
    def test_submit_workout_exception(self, mock_boto3, parse_workout_module):
        """Test exception handling in workout submission."""
        # Setup mock to raise exception
        mock_lambda = MagicMock()
        mock_boto3.return_value = mock_lambda
        mock_lambda.invoke.side_effect = Exception("Test error")
        
        # Execute
        service = parse_workout_module.WorkoutSubmissionService()
        workout = parse_workout_module.WorkoutData({
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        })
        success, workout_id = service.submit_workout(workout, "test-user")
        
        # Verify error is handled gracefully
        assert success is False
        assert workout_id is None

    def test_get_function_info(self, parse_workout_module):
        """Test getting function information."""
        # Test with default function name
        service1 = parse_workout_module.WorkoutSubmissionService()
        info1 = service1.get_function_info()
        assert info1["function_name"] == "submit-workout"
        assert info1["service"] == "AWS Lambda"
        assert "region" in info1
        
        # Test with custom function name
        service2 = parse_workout_module.WorkoutSubmissionService(function_name="custom-function")
        info2 = service2.get_function_info()
        assert info2["function_name"] == "custom-function"


class TestWorkoutService:
    """Test cases for the WorkoutService class."""

    def test_process_message_valid_workout(self, parse_workout_module):
        """Test processing a message with valid workout data."""
        # Setup mocks
        mock_llm = MagicMock()
        mock_llm.extract_workout.return_value = {
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        }
        
        mock_submission = MagicMock()
        mock_submission.submit_workout.return_value = (True, "test-workout-id")
        
        # Execute
        service = parse_workout_module.WorkoutService(llm_service=mock_llm, submission_service=mock_submission)
        result = service.process_message(
            "I did bench press 3x8 at 135 lbs",
            [],
            "test-user"
        )
        
        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["workout"]["exercise"] == "bench press"
        assert response_body["saved"] is True
        assert response_body["workout_id"] == "test-workout-id"
        
        # Verify services were called correctly
        mock_llm.extract_workout.assert_called_with("I did bench press 3x8 at 135 lbs", [])
        mock_submission.submit_workout.assert_called_once()

    def test_process_message_extraction_failure(self, parse_workout_module):
        """Test handling extraction failure."""
        # Setup mock to return None (extraction failed)
        mock_llm = MagicMock()
        mock_llm.extract_workout.return_value = None
        
        # Execute
        service = parse_workout_module.WorkoutService(llm_service=mock_llm)
        result = service.process_message(
            "I did something today",
            [],
            "test-user"
        )
        
        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert "missing_fields" in response_body
        assert len(response_body["missing_fields"]) > 0

    def test_process_message_missing_fields(self, parse_workout_module):
        """Test handling missing fields in workout data."""
        # Setup mock to return incomplete data
        mock_llm = MagicMock()
        mock_llm.extract_workout.return_value = {
            "exercise": "bench press",
            # Missing weight, reps, sets
        }
        
        # Execute
        service = parse_workout_module.WorkoutService(llm_service=mock_llm)
        result = service.process_message(
            "I did bench press today",
            [],
            "test-user"
        )
        
        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert "workout" in response_body
        assert "missing_fields" in response_body
        assert len(response_body["missing_fields"]) == 3  # weight, reps, sets
        assert "message" in response_body
        assert "Please provide" in response_body["message"]

    def test_process_message_submission_failure(self, parse_workout_module):
        """Test handling submission failure."""
        # Setup mocks
        mock_llm = MagicMock()
        mock_llm.extract_workout.return_value = {
            "exercise": "bench press",
            "weight": 135,
            "reps": 8,
            "sets": 3
        }
        
        mock_submission = MagicMock()
        mock_submission.submit_workout.return_value = (False, None)  # Submission failed
        
        # Execute
        service = parse_workout_module.WorkoutService(llm_service=mock_llm, submission_service=mock_submission)
        result = service.process_message(
            "I did bench press 3x8 at 135 lbs",
            [],
            "test-user"
        )
        
        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["saved"] is False
        assert response_body["workout_id"] is None
        assert "Failed to save" in response_body["message"]

    def test_get_service_info(self, parse_workout_module):
        """Test getting service information."""
        # Setup
        mock_llm = MagicMock()
        mock_llm.get_model_info.return_value = {"model_id": "test-model"}
        
        mock_submission = MagicMock()
        mock_submission.get_function_info.return_value = {"function_name": "test-function"}
        
        # Execute
        service = parse_workout_module.WorkoutService(llm_service=mock_llm, submission_service=mock_submission)
        info = service.get_service_info()
        
        # Verify
        assert "llm_service" in info
        assert info["llm_service"]["model_id"] == "test-model"
        assert "submission_service" in info
        assert info["submission_service"]["function_name"] == "test-function"


class TestRequestHandler:
    """Test cases for the RequestHandler class."""

    def test_parse_request(self, parse_workout_module):
        """Test parsing request parameters from different event formats."""
        # Setup
        handler = parse_workout_module.RequestHandler()
        
        # Test with parameters in body
        event1 = {
            "body": {
                "userId": "user1",
                "message": "I did bench press today",
                "chat_history": [{"role": "user", "content": "Hello"}]
            }
        }
        message1, history1, user_id1 = handler.parse_request(event1)
        assert message1 == "I did bench press today"
        assert history1 == [{"role": "user", "content": "Hello"}]
        assert user_id1 == "user1"
        
        # Test with string body
        event2 = {
            "body": json.dumps({
                "userId": "user2",
                "message": "I did squats today",
            })
        }
        message2, history2, user_id2 = handler.parse_request(event2)
        assert message2 == "I did squats today"
        assert history2 == []  # Default empty history
        assert user_id2 == "user2"
        
        # Test with snake_case user_id
        event3 = {
            "body": {
                "user_id": "user3",
                "message": "I did deadlifts today",
            }
        }
        message3, history3, user_id3 = handler.parse_request(event3)
        assert message3 == "I did deadlifts today"
        assert user_id3 == "user3"
        
        # Test with empty event
        event4 = {}
        message4, history4, user_id4 = handler.parse_request(event4)
        assert message4 == ""
        assert history4 == []
        assert user_id4 == "anonymous"  # Default user ID

    def test_handle_valid_message(self, parse_workout_module):
        """Test handling a valid message."""
        # Setup mock workout service
        mock_service = MagicMock()
        mock_service.process_message.return_value = {
            "statusCode": 200,
            "body": json.dumps({"workout": {"exercise": "bench press"}})
        }
        
        # Setup handler with mock service
        handler = parse_workout_module.RequestHandler(workout_service=mock_service)
        
        # Execute
        event = {
            "body": {
                "userId": "test-user",
                "message": "I did bench press today"
            }
        }
        result = handler.handle(event)
        
        # Verify
        assert result["statusCode"] == 200
        mock_service.process_message.assert_called_with(
            "I did bench press today", [], "test-user"
        )

    def test_handle_missing_message(self, parse_workout_module):
        """Test handling a request with missing message."""
        # Setup
        handler = parse_workout_module.RequestHandler()
        
        # Execute
        event = {
            "body": {
                "userId": "test-user",
                # Missing message
            }
        }
        result = handler.handle(event)
        
        # Verify
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert "Message is required" in response_body["error"]

    def test_handle_error(self, parse_workout_module):
        """Test error handling in request handler."""
        # Setup
        handler = parse_workout_module.RequestHandler()
        
        # Execute with invalid JSON
        event = {
            "body": "this is not valid JSON"
        }
        result = handler.handle(event)
        
        # Verify
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert "Internal server error" in response_body["error"]

    def test_get_health_check(self, parse_workout_module):
        """Test health check endpoint."""
        # Setup mock workout service
        mock_service = MagicMock()
        mock_service.get_service_info.return_value = {
            "llm_service": {"model_id": "test-model"},
            "submission_service": {"function_name": "test-function"}
        }
        
        # Setup handler with mock service
        handler = parse_workout_module.RequestHandler(workout_service=mock_service)
        
        # Execute
        result = handler.get_health_check()
        
        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["status"] == "healthy"
        assert "services" in response_body
        assert "llm_service" in response_body["services"]
        assert "submission_service" in response_body["services"]


class TestLambdaHandler:
    """Test cases for the Lambda handler function."""

    def test_lambda_handler(self, parse_workout_module):
        """Test the Lambda handler function."""
        # Create a patched version of the request_handler
        with patch.object(parse_workout_module, 'request_handler') as mock_handler:
            # Setup mock response
            mock_handler.handle.return_value = {
                "statusCode": 200,
                "body": json.dumps({"test": "success"})
            }
            
            # Execute
            event = {"body": {"message": "test message"}}
            result = parse_workout_module.lambda_handler(event, None)
            
            # Verify
            assert result["statusCode"] == 200
            response_body = json.loads(result["body"])
            assert response_body["test"] == "success"
            mock_handler.handle.assert_called_with(event) 