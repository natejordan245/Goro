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
- [x] Compatibility
  - Support for both camelCase and snake_case parameter names
  - JSON serialization handling for Decimal types

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
  - Improve parsing accuracy and consistency
  - Add support for multiple exercises in a single message
  - Add exercise grouping and workout session tracking
  - Add support for rest periods between exercises
  - Add support for exercise order and sequence

### API Gateway
- [x] REST API Setup
  - Created new REST API
  - Configured endpoints:
    - POST `/submitWorkout`
    - GET `/getWorkouts`
  - Enabled CORS
  - Set up request/response integration
  - Deployed to dev stage

### Testing Infrastructure
- [x] Comprehensive Test Suite
  - Created modular test organization with shared fixtures
  - Unit tests for all Lambda functions (57 tests total)
  - Tests for all success and error paths
  - Mocked AWS services (DynamoDB, Lambda, Bedrock)
- [x] Test Utilities
  - `conftest.py` with shared fixtures and configurations
  - Dynamic module importing across Lambda directories
  - Test runners with optional coverage and filtering
  - Environment setup and cleanup
- [x] DynamoDB Testing
  - Mock tables with proper indexes
  - Sample data population
  - Decimal handling for numeric types
- [x] Lambda Integration Tests
  - Tests for cross-Lambda interactions
  - API validation and error handling
  - Input/output format verification

### Deployment Infrastructure
- [x] Lambda Layer
  - Shared dependencies layer
  - boto3 configuration
  - Attached to all functions
- [x] Deployment Scripts
  - Moved to dedicated bat_scripts directory
  - Refactored for better maintainability
  - Enhanced error handling and reporting
- [x] Test Runners
  - Python script with customizable options
  - Windows batch file for easy execution
  - Support for running specific Lambda tests

## Recent Progress (May 2024)
### Infrastructure Improvements
- [x] Restructured DynamoDB data model with GSIs for efficient queries
- [x] Optimized Lambda functions for performance and code quality
- [x] Enhanced error handling and input validation
- [x] Added comprehensive documentation with input/output schemas
- [x] Implemented best practices for AWS resource usage
- [x] Set up API Gateway with REST endpoints
- [x] Fixed JSON serialization issues for Decimal types
- [x] Created comprehensive test suite for all Lambda functions

### Code Refactoring
- [x] Implemented proper separation of concerns (repository/service/handler pattern)
- [x] Standardized response formats across all Lambda functions
- [x] Created utility modules for shared functionality
- [x] Enhanced error handling with detailed error messages
- [x] Improved module organization with clean imports
- [x] Added proper type annotations throughout the codebase
- [x] Standardized logging patterns for better observability

### Testing Infrastructure
- [x] Implemented pytest fixtures for mocking AWS services
- [x] Created dynamic module importing for cross-Lambda tests
- [x] Added test runners with filtering capabilities
- [x] Fixed import path issues for module dependencies
- [x] Added proper handling of DynamoDB Decimal types
- [x] Implemented test helpers for common operations

### Technical Achievements
- [x] Designed efficient querying patterns for workout data
- [x] Created abstracted validation framework for exercise data
- [x] Implemented personal record tracking and progress measurement
- [x] Structured modular codebase with clear separation of concerns
- [x] Added future improvement roadmaps to all components
- [x] Built comprehensive test coverage for all code paths

### Current Approach
- [x] Decision to implement conversation state on client-side
  - Simplified backend architecture
  - Reduced AWS costs and complexity
  - Better performance and offline capabilities
  - Enhanced privacy with sensitive data on device

### Current Issues
- [ ] parse-workout Lambda needs improvement for parsing accuracy
- [ ] Need to implement WebSocket API for real-time chat
- [ ] Frontend development to begin

# Part 2: Project Schedule & Upcoming Tasks

## Immediate Next Steps
- [ ] WebSocket API Setup
  - Create WebSocket API in API Gateway
  - Implement connect/disconnect handlers
  - Create message routing
  - Integrate with parse-workout Lambda

- [ ] Frontend Foundation
  - Initialize React Native with expo
  - Set up navigation
  - Create base screens
  - Implement chat interface
  - Build state management for conversation flow

- [ ] Testing Enhancements
  - Add integration tests for WebSocket API
  - Create end-to-end testing framework
  - Add load testing for Lambda functions
  - Create mocks for frontend testing

## Later Tasks
- [ ] Complete Chat Implementation
  - Build client-side conversation state management
  - Implement follow-up question generation
  - Create UI for chat history
  - Connect to WebSocket API

- [ ] Workout History & Visualization
  - Implement workout history view
  - Create progress charts
  - Add personal record tracking
  - Build filtering and sorting options

## Optional Stretch Goals
- [ ] User Authentication
- [ ] Push Notifications
- [ ] Workout Templates
- [ ] Export & Sharing Features

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
   - Use pytest fixtures for AWS service mocking
   - Ensure proper handling of DynamoDB Decimal types
   - Test all error handling paths

## AWS Best Practices
1. IAM Permissions
   - Use principle of least privilege
   - Create specific policies per function
   - Document required permissions

2. DynamoDB
   - Handle reserved keywords
   - Use expression attributes
   - Optimize query efficiency
   - Use Decimal types for numeric values
   - Create appropriate indexes for query patterns

3. Error Handling
   - Use specific AWS exceptions
   - Provide clear error messages
   - Implement proper logging

## Documentation Requirements
1. Update README.MD with:
   - Completed tasks
   - Requirement changes
   - New features
   - Technical decisions

2. Test Documentation
   - Success scenarios
   - Error cases
   - Edge cases
   - Mocking approach

## Recent Progress 
### Infrastructure Improvements
- [x] Created and configured parse-workout Lambda function
- [x] Set up shared Lambda Layer (version 7) for all functions
- [x] Cleaned up deployment scripts
  - Modified create-layer.bat to handle all functions
  - Updated deploy.bat to only deploy lambda_function.py
- [x] Configured Bedrock access with Titan Text Lite model
- [x] Set up IAM roles and permissions
- [x] Built comprehensive test suite for all Lambda functions
  - 57 tests covering all components and error paths
  - Shared fixtures for AWS service mocking
  - Customizable test runners

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

### Next Steps for Future AI Assistants
1. **WebSocket Implementation**
   - Create WebSocket API in API Gateway
   - Implement connection management Lambda
   - Build message routing system
   - Connect to existing Lambda functions

2. **Frontend Development**
   - Set up React Native project structure
   - Create chat interface components
   - Implement WebSocket connection handling
   - Build state management for chat history

3. **Test Suite Expansion**
   - Add WebSocket API tests
   - Create frontend component tests
   - Implement end-to-end testing framework
   - Add performance testing

4. **Conversation Flow Improvement**
   - Enhance parse-workout to better handle partial data
   - Implement stateful conversation tracking
   - Create follow-up question generation
   - Add support for multiple exercises in a single conversation