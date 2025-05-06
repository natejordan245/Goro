"""
AWS Lambda function for storing workout data in DynamoDB.
Handles workout submission with validation for exercise data structure and types.

Input Format:
------------
{
    "body": {
        "userId": "string",           # Required: User's unique identifier
        "exercises": [                # Required: Array of exercise objects
            {
                "name": "string",     # Required: Name of the exercise
                "weight": number,     # Required: Weight used (can be 0 for bodyweight)
                "reps": integer,      # Required: Number of repetitions (must be > 0)
                "sets": integer       # Required: Number of sets (must be > 0)
            },
            ...
        ]
    }
}

Output Format:
-------------
Success (200):
{
    "statusCode": 200,
    "headers": {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    },
    "body": {
        "message": "Workout saved successfully",
        "workoutIds": ["string", ...],  # List of generated workout IDs
        "date": "YYYY-MM-DD",           # Date the workout was recorded
        "count": integer                # Number of exercises saved
    }
}

Error (400, 500):
{
    "statusCode": 400/500,
    "headers": {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    },
    "body": {
        "error": "Error message"        # Description of what went wrong
    }
}

Future Improvements:
------------------
Data Enhancements:
- Add support for additional exercise attributes (e.g., duration, distance, notes)
- Implement exercise name standardization using a predefined exercise list
- Support for supersets and circuit training workouts
- Add validation for reasonable weight/rep ranges by exercise type

Performance & Reliability:
- Implement idempotency with request IDs to prevent duplicate submissions
- Add retry logic for DynamoDB failures with exponential backoff
- Add conditional writes to prevent overwriting existing data
- Consider using SQS for asynchronous processing of larger workout batches

User Experience:
- Provide more detailed error messages with suggestions for correction
- Support bulk imports from third-party fitness apps
- Add workout templates for common exercise routines
- Support for workout photos or video links

Security & Compliance:
- Add stricter validation for user input to prevent injection attacks
- Implement fine-grained access control for shared accounts
- Add auditing for workout modifications
- Support data export for GDPR compliance

Analytics:
- Add workout categorization (strength, cardio, flexibility)
- Calculate and store derived metrics (volume, intensity, estimated calories)
- Track personal records and highlight achievements
- Generate weekly/monthly summary data for reporting
"""

import json
import time
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Tuple
import boto3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('UserWorkouts')

def validate_exercise(exercise: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a single exercise object.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = {'name', 'weight', 'reps', 'sets'}
    # Check if exercise is a dictionary
    if not isinstance(exercise, dict):
        return False, "Exercise must be a dictionary"

    # Check if required fields are present
    if missing := required_fields - exercise.keys():
        return False, f"Missing required fields: {missing}"

    # Define validation rules as (condition, error_message) pairs
    validation_rules = [
        (lambda: not isinstance(exercise['name'], str),
         "Exercise name must be a string"),
        (lambda: not isinstance(exercise['weight'], (int, float)),
         "Weight must be a number"),
        (lambda: not isinstance(exercise['reps'], int),
         "Reps must be an integer"),
        (lambda: not isinstance(exercise['sets'], int),
         "Sets must be an integer"),
        (lambda: exercise['weight'] < 0,
         "Weight cannot be negative"),
        (lambda: exercise['reps'] <= 0,
         "Reps must be positive"),
        (lambda: exercise['sets'] <= 0,
         "Sets must be positive"),
    ]

    # Check each validation rule
    for check_condition, error_message in validation_rules:
        if check_condition():
            return False, error_message

    return True, None

def lambda_handler(event: Dict[str, Any], _: Any) -> Dict[str, Any]:
    """Handle incoming workout data, validate it, and store in DynamoDB."""
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        user_id = body.get('userId')
        exercises = body.get('exercises', [])

        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'userId is required'})
            }

        if not isinstance(exercises, list) or not exercises:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'exercises must be a non-empty array'})
            }

        # Validate all exercises
        for i, exercise in enumerate(exercises):
            is_valid, error_message = validate_exercise(exercise)
            if not is_valid:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Invalid exercise at index {i}: {error_message}'
                    })
                }

        # Create items for DynamoDB with new key structure
        timestamp = int(time.time())
        date_string = datetime.now().strftime('%Y-%m-%d')
        saved_workout_ids = []

        # Use batch writer for efficiency with multiple items
        with table.batch_writer() as batch:
            for i, exercise in enumerate(exercises):
                # Create a workoutId that includes date, timestamp, and index for uniqueness
                workout_id = f"DATE#{date_string}#TIME#{timestamp}#{i}"

                # Create a userId_exercise composite key for exercise-based queries
                user_id_exercise = f"{user_id}#EXERCISE#{exercise['name']}"

                # Create the item with the new structure
                item = {
                    'userId': user_id,                  # Primary partition key
                    'workoutId': workout_id,            # Primary sort key
                    'userId_exercise': user_id_exercise, # GSI2 partition key
                    'date': date_string,                # GSI1 sort key
                    'timestamp': str(timestamp),        # GSI2 sort key - CHANGED TO STRING
                    'exercise': exercise['name'],
                    'sets': int(exercise['sets']),
                    'reps': int(exercise['reps']),
                    'weight': Decimal(str(round(float(exercise['weight']), 2))),
                }
                batch.put_item(Item=item)
                saved_workout_ids.append(workout_id)

        logger.info("Saved %s exercises for user %s", len(saved_workout_ids), user_id)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Workout saved successfully',
                'workoutIds': saved_workout_ids,
                'date': date_string,
                'count': len(saved_workout_ids)
            })
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON format in request body")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Invalid JSON format in request body'})
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in lambda_handler: %s", str(e), exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

# The save_workout_to_dynamodb function has been removed as it was unused and contained errors
