"""
AWS Lambda function for parsing workout information from user messages.
Uses Claude Instant to extract structured workout data and saves to DynamoDB.

Input Format:
------------
{
    "body": {
        "message": "string",          # Required: User's workout message
        "chat_history": [             # Optional: Previous conversation context
            {
                "role": "string",     # "user" or "assistant"
                "content": "string"   # Message content
            },
            ...
        ],
        "user_id": "string"          # Required: User's unique identifier
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
        "workout": {
            "exercise": "string",
            "weight": number,
            "reps": integer,
            "sets": integer
        },
        "saved": boolean,
        "workout_id": "string",
        "message": "string"
    }
}

Missing Fields (200):
{
    "statusCode": 200,
    "body": {
        "workout": {
            "exercise": "string",
            "weight": number | null,
            "reps": integer | null,
            "sets": integer | null
        },
        "missing_fields": ["string", ...],
        "message": "string"
    }
}

Error (400/500):
{
    "statusCode": 400/500,
    "body": {
        "error": "Error message"
    }
}

Future Improvements:
------------------
Performance & Scaling:
- Implement caching for Claude responses to reduce API calls
- Add rate limiting for Bedrock API calls
- Optimize prompt engineering for better extraction accuracy

Code Structure:
- Abstract Bedrock operations into a separate service layer
- Implement proper conversation state management
- Add more robust validation using a library like Pydantic
- Create separate modules for exercise name standardization

Feature Enhancements:
- Support for workout notes and comments
- Add exercise variation detection
- Implement workout template matching
- Add support for supersets and circuit training
- Track personal records and achievements

Security & Compliance:
- Add input sanitization for user messages
- Implement proper error masking
- Add request validation middleware
- Implement proper logging and monitoring

Testing & Reliability:
- Add comprehensive unit tests
- Create integration tests with Bedrock
- Add retry logic for API failures
- Implement proper error recovery
"""

import json
import re
import difflib
import time
import logging
from decimal import Decimal
from datetime import datetime
import boto3
from exercises import KNOWN_EXERCISES

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('UserWorkouts')

def map_exercise_name(extracted_name):
    """Map user input to standardized exercise name."""
    name = extracted_name.lower().strip()
    if name in KNOWN_EXERCISES:
        return name
    matches = difflib.get_close_matches(name, KNOWN_EXERCISES, n=1, cutoff=0.8)
    return matches[0] if matches else name

def validate_workout_data(workout_data):
    """
    Validate the structure and types of workout data.
    Returns tuple of (is_valid, missing_fields).
    """
    if not isinstance(workout_data, dict):
        logger.warning("Claude returned non-dict JSON")
        return False, ["exercise", "sets", "reps", "weight"]

    # Ensure exercise field exists and is a string
    exercise = workout_data.get('exercise')
    if not isinstance(exercise, str):
        logger.warning("Invalid exercise field: %s", exercise)
        return False, ["exercise", "sets", "reps", "weight"]

    # Map exercise name
    workout_data['exercise'] = map_exercise_name(exercise)

    # Check for missing required fields
    missing_fields = []
    if not workout_data.get('exercise'):
        missing_fields.append('exercise')
    if workout_data.get('weight') is None:  # Only check for None, not <= 0
        missing_fields.append('weight')
    if workout_data.get('reps') is None or workout_data['reps'] <= 0:
        missing_fields.append('reps')
    if workout_data.get('sets') is None or workout_data['sets'] <= 0:
        missing_fields.append('sets')

    return len(missing_fields) == 0, missing_fields

def normalize_numeric_fields(workout_data):
    """Convert and normalize numeric fields in workout data."""
    for field in ['weight', 'reps', 'sets']:
        try:
            value = workout_data.get(field)
            if value is not None:
                workout_data[field] = float(value) if field == 'weight' else int(value)
        except (ValueError, TypeError):
            workout_data[field] = None
    return workout_data

def extract_workout_data(message, chat_history):
    """
    Extract workout data from user message using Claude.
    Returns tuple of (workout_data, missing_fields).
    """
    # Build context from chat history
    context = "\n".join([
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in chat_history[-5:]  # Last 5 turns for context
    ]) if chat_history else ""

    # Construct prompt for Claude
    prompt = (
        "Extract workout information from this text. Return ONLY a JSON object with these fields:\n"
        "{\n"
        "  \"exercise\": \"EXERCISE NAME IN UPPERCASE\",\n"
        "  \"sets\": number or null,\n"
        "  \"reps\": number or null,\n"
        "  \"weight\": number in pounds or null\n"
        "}\n"
        "If a field is missing or unclear, use null.\n"
        "IMPORTANT: The exercise name MUST be in UPPERCASE letters.\n"
        "For bodyweight/calisthenics exercises, set weight to 0.\n"
        "Unless otherwise specified, the format the user says their info is weight, reps, sets.\n"
    )

    if context:
        prompt += f"\nPrevious context:\n{context}\n"
    prompt += f"\nCurrent message: {message}"

    # Call Claude
    try:
        # Updated Bedrock request format
        response = bedrock.invoke_model(
            modelId='anthropic.claude-instant-v1',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "temperature": 0,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            })
        )

        # Extract JSON from response
        response_body = json.loads(response['body'].read())
        # Claude returns a list of content blocks, we want the first one
        response_text = response_body.get('content', [{}])[0].get('text', '')

        # Log the raw response for debugging
        logger.info("Raw Claude response: %s", response_text)

        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            logger.warning("No JSON found in response: %s", response_text)
            return None, ["exercise", "sets", "reps", "weight"]

        try:
            workout_data = json.loads(json_match.group(0))
            # Force exercise name to uppercase
            if workout_data.get('exercise'):
                workout_data['exercise'] = workout_data['exercise'].upper()

            workout_data = normalize_numeric_fields(workout_data)
            _, missing_fields = validate_workout_data(workout_data)  # Use _ to ignore is_valid

            # Return the workout data even if it's incomplete
            return workout_data, missing_fields

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from Claude: %s", str(e))
            return None, ["exercise", "sets", "reps", "weight"]

    except (boto3.exceptions.Boto3Error, json.JSONDecodeError) as e:
        logger.error("Error extracting workout data: %s", str(e))
        return None, ["exercise", "sets", "reps", "weight"]

def save_workout(workout_data, user_id):
    """Save workout data to DynamoDB."""
    try:
        timestamp = int(time.time())
        date_string = datetime.now().strftime('%Y-%m-%d')
        workout_id = f"DATE#{date_string}#TIME#{timestamp}"
        item = {
            'userId': user_id,
            'workoutId': workout_id,
            'userId_exercise': f"{user_id}#EXERCISE#{workout_data['exercise']}",
            'date': date_string,
            'timestamp': str(timestamp),  # Convert to string for GSI
            'exercise': workout_data['exercise'],
            'sets': int(workout_data['sets']),
            'reps': int(workout_data['reps']),
        }

        # Handle weight field separately for clarity
        weight_value = workout_data['weight']

        # Convert weight to Decimal with proper handling for None values
        if weight_value is None:
            item['weight'] = Decimal('0')
        else:
            # Round to 2 decimal places and convert to Decimal for DynamoDB
            rounded_weight = round(weight_value, 2)
            item['weight'] = Decimal(str(rounded_weight))

        table.put_item(Item=item)
        return True, workout_id
    except (boto3.exceptions.Boto3Error, ValueError) as e:
        logger.error("Error saving workout: %s", str(e))
        return False, None

def lambda_handler(event, _):
    """Main Lambda handler."""
    try:
        # Parse request
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        message = body.get('message', '')
        chat_history = body.get('chat_history', [])
        user_id = body.get('user_id', 'anonymous')

        if not message:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Message is required'})
            }

        # Extract workout data
        workout_data, missing_fields = extract_workout_data(message, chat_history)

        # If we have no workout data at all
        if workout_data is None:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'error': 'Could not extract workout data',
                    'missing_fields': ["exercise", "sets", "reps", "weight"]
                })
            }

        # If we have missing fields, return partial data for follow-up
        if missing_fields:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'workout': workout_data,  # Include the partial workout data
                    'missing_fields': missing_fields,
                    'message': f"Please provide: {', '.join(missing_fields)}"
                })
            }

        # Save complete workout
        success, workout_id = save_workout(workout_data, user_id)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'workout': workout_data,
                'saved': success,
                'workout_id': workout_id if success else None,
                'message': 'Workout saved successfully' if success else 'Failed to save workout'
            })
        }

    except (json.JSONDecodeError, boto3.exceptions.Boto3Error) as e:
        logger.error("Error in lambda_handler: %s", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
