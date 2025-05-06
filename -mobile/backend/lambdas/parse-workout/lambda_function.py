import json
import boto3
import re
import difflib
import time
import uuid
import logging
from decimal import Decimal
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('UserWorkouts')

# Your large set of KNOWN_EXERCISES here
KNOWN_EXERCISES = {
    "bench press", "squat", "deadlift", "overhead press", "pull up", "row", "curl", "tricep extension",
    # ... (your full list of exercises)
}

def map_exercise_name(extracted_name):
    name = extracted_name.lower().strip()
    # Exact match
    if name in KNOWN_EXERCISES:
        return name
    # Fuzzy match (returns closest match if similarity > 0.8)
    matches = difflib.get_close_matches(name, KNOWN_EXERCISES, n=1, cutoff=0.8)
    if matches:
        return matches[0]
    return name  # fallback to original if no match

def get_missing_field_and_question(workout):
    """
    Check if any required fields are missing and return a follow-up question.
    Returns (field_name, question) if a field is missing, or (None, None) if all fields are present.
    """
    questions = {
        "exercise": "What exercise did you do?",
        "weight": "How much weight did you use?",
        "reps": "How many reps did you do?",
        "sets": "How many sets did you do?"
    }
    
    for field in ["exercise", "weight", "reps", "sets"]:
        value = workout.get(field)
        # Exercise can't be empty, and number fields can't be None, 0, or negative
        if field == "exercise":
            if not value or not isinstance(value, str) or value.strip() == "":
                return field, questions[field]
        else:
            if value is None or not isinstance(value, (int, float)) or value <= 0:
                return field, questions[field]
    
    return None, None

def save_workout_to_dynamodb(workout, user_id):
    """
    Save a workout to DynamoDB with optimized keys for date and exercise-based queries.
    """
    timestamp = int(time.time())
    date_string = datetime.now().strftime('%Y-%m-%d')
    
    # Create a workoutId that includes date and timestamp for natural ordering
    workout_id = f"DATE#{date_string}#TIME#{timestamp}"
    
    # Create a userId_exercise composite key for exercise-based queries
    userId_exercise = f"{user_id}#EXERCISE#{workout['exercise']}"
    
    # Convert workout data to DynamoDB format
    item = {
        'userId': user_id,                  # Primary partition key
        'workoutId': workout_id,            # Primary sort key
        'userId_exercise': userId_exercise, # GSI2 partition key 
        'date': date_string,                # GSI1 sort key
        'timestamp': timestamp,             # GSI2 sort key
        'exercise': workout['exercise'],
        'sets': int(workout['sets']),
        'reps': int(workout['reps']),
        'weight': Decimal(str(round(workout['weight'], 2))),  # Round to 2 decimal places
    }
    
    try:
        response = table.put_item(Item=item)
        return True, workout_id
    except Exception as e:
        logger.error(f"Error saving to DynamoDB: {str(e)}")
        return False, None

def lambda_handler(event, context):
    try:
        # Parse the incoming event body (accepts both string and dict)
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        
        # Get message and chat history
        message = body.get('message', '')
        chat_history = body.get('chat_history', [])
        user_id = body.get('user_id', 'anonymous')
        
        # Log the incoming request
        logger.info(f"Received request from user {user_id}: {message}")
        if chat_history:
            logger.info(f"Chat history length: {len(chat_history)}")
        
        if not message:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Message is required'})
            }

        # Instructions for Claude
        instructions = (
            "Extract workout information from this text and return it in this exact JSON format:\n"
            "{\n"
            "  \"exercise\": \"exercise name in lowercase\",\n"
            "  \"sets\": number,\n"
            "  \"reps\": number,\n"
            "  \"weight\": number in pounds (decimal okay)\n"
            "}\n"
            "Only include these exact fields. Convert all weights to pounds. If any field is missing, use null."
        )

        # Build the context message with the previous 10 messages
        context_prompt = ""
        if chat_history:
            # Only include the last 10 messages (5 turns)
            limited_history = chat_history[-10:]
            for msg in limited_history:
                if msg.get('role') == 'user':
                    context_prompt += f"User: {msg.get('content')}\n"
                elif msg.get('role') == 'assistant':
                    context_prompt += f"Assistant: {msg.get('content')}\n"
        
        # Build the payload for Claude Instant
        final_prompt = instructions
        if context_prompt:
            final_prompt += "\n\nPrevious conversation context:\n" + context_prompt
        final_prompt += "\n\nCurrent message to parse: " + message

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            "max_tokens": 512,
            "temperature": 0,
            "top_p": 1,
            "anthropic_version": "bedrock-2023-05-31"
        }

        # Call Claude Instant
        response = bedrock.invoke_model(
            modelId='anthropic.claude-instant-v1',
            body=json.dumps(payload)
        )
        response_body = json.loads(response['body'].read())
        claude_output = response_body.get('content', response_body.get('claude_output', ''))

        # Log Claude's raw output for debugging
        logger.info(f"Claude raw output: {claude_output}")

        # If output is a list (as in some Claude responses), get the first item's text
        if isinstance(claude_output, list) and len(claude_output) > 0:
            claude_text = claude_output[0].get('text', '')
        else:
            claude_text = claude_output

        # Extract JSON from Claude's text using regex
        json_match = re.search(r'\{[\s\S]*\}', claude_text)
        if not json_match:
            logger.warning(f"No JSON found in Claude output: {claude_text}")
            return {
                'statusCode': 200,
                'body': json.dumps({'error': 'No JSON found in Claude output', 'claude_output': claude_text})
            }
        workout_json = json.loads(json_match.group(0))
        logger.info(f"Extracted workout JSON: {workout_json}")

        # Standardize the exercise name
        workout_json['exercise'] = map_exercise_name(workout_json.get('exercise', ''))
        
        # Data normalization - ensure numbers are always returned as numbers
        try:
            if workout_json.get('weight') is not None:
                workout_json['weight'] = float(workout_json['weight'])
                # Round weight to 2 decimal places for consistency
                workout_json['weight'] = round(workout_json['weight'], 2)
            if workout_json.get('reps') is not None:
                workout_json['reps'] = int(workout_json['reps'])
            if workout_json.get('sets') is not None:
                workout_json['sets'] = int(workout_json['sets'])
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting numeric fields: {str(e)}")
            # Continue anyway, as we'll catch invalid values in the missing field check

        # Check for missing fields and prepare a follow-up if needed
        missing_field, question = get_missing_field_and_question(workout_json)
        response_json = {'workout': workout_json}
        
        if missing_field:
            logger.info(f"Missing field detected: {missing_field}")
            response_json['missing_field'] = missing_field
            response_json['question'] = question
        else:
            # All fields are present, save to DynamoDB
            logger.info(f"All fields present, saving workout to DynamoDB")
            success, workout_id = save_workout_to_dynamodb(workout_json, user_id)
            if success:
                response_json['saved'] = True
                response_json['workout_id'] = workout_id
                response_json['message'] = f"Workout saved successfully! {workout_json['exercise']}: {workout_json['weight']} lbs, {workout_json['sets']} sets of {workout_json['reps']} reps."
            else:
                response_json['saved'] = False
                response_json['message'] = "Workout parsed but could not be saved to database."
            
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_json)
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }