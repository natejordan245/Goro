# Fitness Chatbot Project Plan
A fitness chatbot app for tracking Progressive Overload using React Native, AWS (API Gateway, Lambda, DynamoDB, Bedrock)

# Part 1: Completed Features & Implementation

## Backend Infrastructure
### DynamoDB
- [x] Table: `UserWorkouts`
  - Partition key: `userId` (string)
  - Sort key: `workoutId` (string)
  - Additional fields: 
    - timestamp (string)
    - date (string)
    - exercise (string)
    - weight (number)
    - reps (number)
    - sets (number)
    - userId_exercise (string) - for GSI
  - Global Secondary Indexes:
    - DateIndex: userId (PK), date (SK)
    - ExerciseIndex: userId_exercise (PK), timestamp (SK)

### Lambda Functions
#### submit-workout
- [x] Core Functionality
  - Validates exercise data (name, weight, reps, sets)
  - Handles both string and JSON body inputs
  - Creates unique workoutId using timestamp and index
  - Uses batch operations for efficient multi-exercise saving
  - Stores workout data in DynamoDB with optimized keys for querying
- [x] Error Handling
  - Comprehensive input validation with detailed messages
  - Type checking and value range validation for all fields
  - DynamoDB operation error handling
  - Structured JSON responses for all error cases
- [x] Code Quality
  - Full type hints with mypy compliance
  - Pylint optimized (9.5+ score)
  - Comprehensive docstrings with input/output formats
  - Optimized validation using rule-based approach

#### get-workouts
- [x] Core Functionality
  - Multiple query types supported:
    - Summary: All workouts grouped by date
    - Date: Workouts for a specific date
    - Exercise: All instances of a specific exercise
    - Progress: Performance metrics for a specific exercise over time
  - Efficient GSI usage for optimal query performance
  - Data transformations for visualization (progress data)
- [x] Advanced Features
  - Volume calculation (weight × reps × sets)
  - Personal record tracking (max weight with date)
  - Chronological sorting (newest first for history)
- [x] Infrastructure
  - CORS enabled
  - Comprehensive error handling
  - Consistent response format
  - Python 3.10+ features (match statements)

#### parse-workout
- [x] Basic Implementation
  - Integration with Bedrock (Claude Instant)
  - JSON extraction from LLM responses
  - Exercise name matching against standardized list
- [x] Recent Improvements:
  - Added support for bodyweight exercises (weight = 0)
  - Fixed validation to handle partial workout data
  - Improved error handling and response structure
  - Added uppercase standardization for exercise names
- [ ] Future Enhancements:
  - Implement conversational memory
  - Add support for multiple exercises in a single message
  - Add exercise grouping and workout session tracking
  - Add support for rest periods between exercises
  - Add support for exercise order and sequence

### Deployment Infrastructure
- [x] Lambda Layer
  - Shared dependencies layer
  - boto3 configuration
  - Attached to all functions
- [x] Deployment Scripts
  - Moved to dedicated bat_scripts directory
  - Refactored for better maintainability
  - Enhanced error handling and reporting

## Recent Progress (April 2024)
### Infrastructure Improvements
- [x] Restructured DynamoDB data model with GSIs for efficient queries
- [x] Optimized Lambda functions for performance and code quality
- [x] Enhanced error handling and input validation
- [x] Added comprehensive documentation with input/output schemas
- [x] Implemented best practices for AWS resource usage

### Technical Achievements
- [x] Designed efficient querying patterns for workout data
- [x] Created abstracted validation framework for exercise data
- [x] Implemented personal record tracking and progress measurement
- [x] Structured modular codebase with clear separation of concerns
- [x] Added future improvement roadmaps to all components

### Current Issues
- [ ] parse-workout Lambda needs improvement for conversational flow
- [ ] Need to complete API Gateway setup
- [ ] Frontend development to begin

## Recent Progress (May 7, 2024)
### parse-workout Lambda Improvements
- [x] Enhanced workout data validation
  - Added support for bodyweight exercises (weight = 0)
  - Improved handling of partial workout data
  - Fixed validation logic to properly handle missing fields
- [x] Code Quality Improvements
  - Removed unused variables
  - Improved error handling
  - Enhanced logging for debugging
- [x] Documentation Updates
  - Added comprehensive future improvements section
  - Updated input/output format documentation
  - Added support for multiple exercises in roadmap

### Current Focus
- [ ] Implementing conversational flow for incomplete workout data
- [ ] Adding support for multiple exercises in a single message
- [ ] Improving exercise name standardization
- [ ] Enhancing error handling and user feedback

# Part 2: Project Schedule & Upcoming Tasks

## Week 1: Remaining Core Architecture
- [ ] API Gateway Setup
  - Create new REST API
  - Configure endpoints:
    - POST `/submitWorkout`
    - GET `/getWorkouts`
  - Enable CORS
  - Set up request/response models

- [ ] Bedrock Integration
  - Configure IAM roles
  - Select Claude model
  - Test basic prompts
  - Create `parse-workout` Lambda

- [ ] Frontend Foundation
  - Initialize React Native with expo
  - Set up navigation
  - Create base screens
  - Add chat input UI

## Week 2: Chatbot Intelligence & Data Flow
### Chatbot Enhancement
- [ ] Implement Conversation Flow
- [ ] Frontend Chat UI
- [ ] Data Integration
- [ ] History View Implementation

## Week 3: Polish & Features
### Core Features
- [ ] End-to-End Testing
- [ ] Error Recovery
- [ ] UI Polish
- [ ] History View Enhancement

### Optional Stretch Goals
- [ ] Progress Charts
- [ ] User Authentication
- [ ] Push Notifications

# Part 3: AI Assistant Guidelines

## Code Quality Standards
1. Pylint Compliance
   - Missing docstrings
   - Import order (standard library before third-party)
   - Unnecessary elif after return
   - Broad exception handling
   - Unused arguments

2. Code Optimization
   - Initialize AWS clients outside handler
   - Use type hints
   - Remove debug print statements
   - Consistent error handling patterns

## Development Approach
1. Teaching Methodology
   - Explain reasoning behind changes
   - Clarify AWS permission requirements
   - Document data structure decisions

2. Incremental Development
   - Start with basic functionality
   - Add validation
   - Improve error handling
   - Optimize and clean up

3. Testing Strategy
   - Provide success case tests
   - Include edge case tests
   - Document expected responses

## AWS Best Practices
1. IAM Permissions
   - Use principle of least privilege
   - Create specific policies per function
   - Document required permissions

2. DynamoDB
   - Handle reserved keywords
   - Use expression attributes
   - Optimize query efficiency

3. Error Handling
   - Use specific AWS exceptions
   - Provide clear error messages
   - Implement proper logging

## Documentation Requirements
1. Update plan.md with:
   - Completed tasks
   - Requirement changes
   - New features
   - Technical decisions

2. Test Documentation
   - Success scenarios
   - Error cases
   - Edge cases

## Recent Progress (March 25, 2024)
### Infrastructure Improvements
- [x] Created and configured parse-workout Lambda function
- [x] Set up shared Lambda Layer (version 7) for all functions
- [x] Cleaned up deployment scripts
  - Modified create-layer.bat to handle all functions
  - Updated deploy.bat to only deploy lambda_function.py
- [x] Configured Bedrock access with Titan Text Lite model
- [x] Set up IAM roles and permissions

### Current Issues
- [ ] parse-workout Lambda having inconsistent parsing results
- [ ] Need to implement conversational flow for incomplete workout data
  ```
  Example desired flow:
  user: "just hit 225"
  bot: "Congrats! On what exercise?"
  user: "on bench press"
  bot: "Cool! for how many reps?"
  user: "I hit it for 1 rep"
  bot: "Well done! How many sets?"
  user: "1"
  ```

### Next Steps
- [ ] Implement stateful conversation handling
  - Store conversation state in DynamoDB
  - Track missing workout parameters
  - Handle follow-up questions
- [ ] Improve workout parsing reliability
- [ ] Test conversation flows
- [ ] Set up WebSocket API for real-time chat