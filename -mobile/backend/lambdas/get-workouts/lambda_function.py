"""
AWS Lambda function for retrieving workout data from DynamoDB.
Supports fetching workout history with date range filtering and exercise-specific queries.

Input Format:
------------
{
    "body": {
        "userId": "string",           # Required: User's unique identifier
        "query_type": "string",       # Optional: Type of query (default: "summary")
                                      # Values: "summary", "date", "exercise", "progress"
        "date": "YYYY-MM-DD",         # Required for "date" query type
        "exercise": "string"          # Required for "exercise" and "progress" query types
    }
}

Output Format:
-------------
Summary Query (default):
{
    "statusCode": 200,
    "headers": {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    },
    "body": {
        "user_id": "string",
        "workout_summary": [
            {
                "date": "YYYY-MM-DD",
                "workouts": [
                    {
                        "userId": "string",
                        "workoutId": "string",
                        "exercise": "string",
                        "sets": integer,
                        "reps": integer,
                        "weight": number,
                        "date": "YYYY-MM-DD",
                        "timestamp": "string",
                        "userId_exercise": "string"
                    },
                    ...
                ]
            },
            ...
        ]
    }
}

Date Query:
{
    "statusCode": 200,
    "body": {
        "date": "YYYY-MM-DD",
        "workouts": [workout objects]
    }
}

Exercise Query:
{
    "statusCode": 200,
    "body": {
        "exercise": "string",
        "workouts": [workout objects]
    }
}

Progress Query:
{
    "statusCode": 200,
    "body": {
        "success": true,
        "exercise": "string",
        "progress_data": [
            {
                "date": "YYYY-MM-DD",
                "weight": number,
                "reps": integer,
                "sets": integer,
                "volume": number
            },
            ...
        ],
        "max_weight": number,
        "max_weight_date": "YYYY-MM-DD"
    }
}

Error:
{
    "statusCode": 400/500,
    "headers": {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    },
    "body": {
        "error": "Error message"
    }
}

Future Improvements:
------------------
Performance & Scaling:
- Implement pagination for large result sets using LastEvaluatedKey
- Add Redis/ElastiCache for frequently accessed data
- Track execution times for performance optimization

Code Structure:
- Abstract DynamoDB operations into a separate data access layer
- Separate business logic from the handler function
- Add more robust validation using a library like Pydantic

Feature Enhancements:
- Calculate workout streaks (consecutive workout days)
- Automatically identify and flag personal records
- Group exercises by muscle groups/categories 
- Calculate workout intensity scores
- Add export capabilities (CSV/PDF)

Security & Compliance:
- Implement more fine-grained authorization checks
- Add parameter encryption for sensitive data
- Implement rate limiting to protect against excessive requests

Testing & Reliability:
- Add comprehensive unit tests
- Create integration tests against actual DynamoDB tables
- Simulate and handle DynamoDB throttling and service failures
"""

import json
import logging
from typing import Dict, Any
import boto3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('UserWorkouts')

def get_workouts_by_date(user_id: str, date: str) -> Dict[str, Any]:
    """
    Get all workouts for a user on a specific date.
    
    Args:
        user_id: The user's unique identifier
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dict with status code and workouts data
    """
    try:
        # Query using GSI1 (DateIndex)
        response = table.query(
            IndexName='DateIndex',
            KeyConditionExpression='userId = :uid AND #date = :date',
            ExpressionAttributeNames={
                '#date': 'date'  # 'date' is a reserved word in DynamoDB
            },
            ExpressionAttributeValues={
                ':uid': user_id,
                ':date': date
            }
        )
        logger.info("Retrieved %s workouts for user %s on %s",
                   len(response.get('Items', [])), user_id, date)
        return {
            'statusCode': 200,
            'body': {
                'date': date,
                'workouts': response.get('Items', [])
            }
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error retrieving workouts by date: %s", str(e))
        return {
            'statusCode': 500,
            'body': {'error': f"Error retrieving workouts: {str(e)}"}
        }

def get_workouts_by_exercise(user_id: str, exercise: str) -> Dict[str, Any]:
    """
    Get all workouts for a specific exercise, sorted by timestamp.
    
    Args:
        user_id: The user's unique identifier
        exercise: Name of the exercise
        
    Returns:
        Dict with status code and workouts data
    """
    try:
        # Create the userId_exercise key
        user_id_exercise = f"{user_id}#EXERCISE#{exercise}"

        # Query using GSI2 (ExerciseIndex)
        response = table.query(
            IndexName='ExerciseIndex',
            KeyConditionExpression='userId_exercise = :uex',
            ExpressionAttributeValues={
                ':uex': user_id_exercise
            },
            ScanIndexForward=False  # Sort in descending order (newest first)
        )

        logger.info("Retrieved %s %s workouts for user %s",
                   len(response.get('Items', [])), exercise, user_id)
        return {
            'statusCode': 200,
            'body': {
                'exercise': exercise,
                'workouts': response.get('Items', [])
            }
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error retrieving workouts by exercise: %s", str(e))
        return {
            'statusCode': 500,
            'body': {'error': f"Error retrieving workouts: {str(e)}"}
        }

def get_user_workout_summary(user_id: str) -> Dict[str, Any]:
    """
    Get a summary of user's workouts grouped by date.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Dict with status code and summary data
    """
    try:
        # Query all workouts for this user using DateIndex for faster retrieval
        response = table.query(
            IndexName='DateIndex',
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={
                ':uid': user_id
            }
        )

        # Group workouts by date
        workouts_by_date = {}
        for item in response.get('Items', []):
            date = item.get('date')
            if date not in workouts_by_date:
                workouts_by_date[date] = []
            workouts_by_date[date].append(item)

        # Sort dates in descending order (newest first)
        sorted_dates = sorted(workouts_by_date.keys(), reverse=True)

        # Build the response
        workout_summary = []
        for date in sorted_dates:
            workout_summary.append({
                'date': date,
                'workouts': workouts_by_date[date]
            })

        logger.info("Retrieved workout summary for user %s (%s days)",
                   user_id, len(workout_summary))
        return {
            'statusCode': 200,
            'body': {
                'user_id': user_id,
                'workout_summary': workout_summary
            }
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error retrieving workout summary: %s", str(e))
        return {
            'statusCode': 500,
            'body': {'error': f"Error retrieving workout summary: {str(e)}"}
        }

def get_exercise_progress(user_id: str, exercise: str) -> Dict[str, Any]:
    """
    Get a user's progress on a specific exercise over time.
    Returns data formatted for charting/visualization.
    
    Args:
        user_id: The user's unique identifier
        exercise: Name of the exercise
        
    Returns:
        Dict with status code and progress data
    """
    try:
        # Get all workouts for this exercise
        result = get_workouts_by_exercise(user_id, exercise)

        if result.get('statusCode') != 200 or not result.get('body', {}).get('workouts'):
            return {
                'statusCode': 200,
                'body': {
                    'success': False,
                    'exercise': exercise,
                    'error': 'No data found for this exercise'
                }
            }

        workouts = result.get('body', {}).get('workouts', [])

        # Format data for visualization (extract dates and weights)
        progress_data = []
        for workout in workouts:
            progress_data.append({
                'date': workout.get('date'),
                'weight': float(workout.get('weight', 0)),
                'reps': int(workout.get('reps', 0)),
                'sets': int(workout.get('sets', 0)),
                # Add a simple volume calculation
                'volume': float(workout.get('weight', 0)) * 
                          int(workout.get('reps', 0)) *
                          int(workout.get('sets', 0))
            })

        # Sort by date (ascending)
        progress_data.sort(key=lambda x: x.get('date', ''))

        # Get max weight and date achieved
        if progress_data:
            max_weight_workout = max(progress_data, key=lambda x: x.get('weight', 0))
            max_weight = max_weight_workout.get('weight', 0)
            max_weight_date = max_weight_workout.get('date', '')
        else:
            max_weight = 0
            max_weight_date = ''

        logger.info("Retrieved progress data for %s for user %s",
                   exercise, user_id)
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'exercise': exercise,
                'progress_data': progress_data,
                'max_weight': max_weight,
                'max_weight_date': max_weight_date
            }
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error getting exercise progress: %s", str(e))
        return {
            'statusCode': 500,
            'body': {
                'success': False,
                'error': str(e)
            }
        }

def lambda_handler(event: Dict[str, Any], _: Any) -> Dict[str, Any]:
    """
    Handle workout data retrieval requests.

    Args:
        event: Lambda event object
        _: Lambda context object (unused)

    Returns:
        Response with status code and body
    """
    try:
        # Get parameters from event
        if isinstance(event.get('body'), str):
            body = json.loads(event.get('body', '{}'))
        else:
            body = event.get('body', {})
        query_params = event.get('queryStringParameters', {}) or {}

        # Extract parameters from body or query params
        user_id = body.get('user_id') or query_params.get('user_id')
        date = body.get('date') or query_params.get('date')
        exercise = body.get('exercise') or query_params.get('exercise')
        query_type = body.get('query_type') or query_params.get('query_type') or 'summary'

        logger.info(
            "Received request: query_type=%s, user_id=%s, date=%s, exercise=%s",
            query_type, user_id, date, exercise
        )

        if not user_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'user_id is required'})
            }

        # Route to appropriate function based on query type
        match query_type:
            case 'date' if date:
                result = get_workouts_by_date(user_id, date)
            case 'exercise' if exercise:
                result = get_workouts_by_exercise(user_id, exercise)
            case 'progress' if exercise:
                result = get_exercise_progress(user_id, exercise)
            case _:  # default
                result = get_user_workout_summary(user_id)

        # Add CORS headers
        if isinstance(result, dict) and 'statusCode' in result:
            result['headers'] = {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
            # Ensure body is a string (JSON)
            if isinstance(result.get('body'), dict):
                result['body'] = json.dumps(result['body'])

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in lambda_handler: %s", str(e))
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
