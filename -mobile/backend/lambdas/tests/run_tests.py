#!/usr/bin/env python3
"""
Test runner for all Lambda functions.
Executes pytest suite and provides a summary of results.

Usage:
  python run_tests.py [options]

Options:
  --unit-only     Run only unit tests
  --cov           Generate coverage report
  --html=DIR      Generate HTML report in the specified directory
  --lambda=NAME   Test only a specific Lambda function (parse-workout, submit-workout, get-workouts)
"""

import os
import sys
import subprocess
import argparse


def check_dependencies():
    """Check if required packages are installed."""
    try:
        import pytest
        import moto
        import boto3
        import importlib
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("\nPlease install the required packages:")
        print("pip install -r requirements-test.txt")
        return False
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        print(f"Current Python version: {sys.version}")
        return False
    
    return True


def run_tests(args):
    """Run pytest with the specified options."""
    # Change to the parent directory (lambdas/)
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Build the pytest command
    cmd = ["python", "-m", "pytest", "tests", "-v"]
    
    # Add coverage if requested
    if args.cov:
        cmd.extend(["--cov=lambdas", "--cov-report=term"])
    
    # Add HTML report if requested
    if args.html:
        cmd.append(f"--html={args.html}")
    
    # Filter to unit tests only if requested
    if args.unit_only:
        cmd.append("-m")
        cmd.append("unit")
    
    # Filter to specific Lambda function if requested
    if args.lambda_name:
        cmd.append(f"tests/test_{args.lambda_name.replace('-', '_')}.py")
    
    # Run the tests
    print(f"Running pytest command: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    return result.returncode


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run tests for all Lambda functions")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--cov", action="store_true", help="Generate coverage report")
    parser.add_argument("--html", metavar="DIR", help="Generate HTML report in the specified directory")
    parser.add_argument("--lambda", dest="lambda_name", help="Test only a specific Lambda function (parse-workout, submit-workout, get-workouts)")
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check if specific Lambda function exists
    if args.lambda_name and args.lambda_name not in ["parse-workout", "submit-workout", "get-workouts"]:
        print(f"Error: Unknown Lambda function: {args.lambda_name}")
        print("Available Lambda functions: parse-workout, submit-workout, get-workouts")
        sys.exit(1)
    
    # Run tests
    print("Running tests for Lambda functions...\n")
    if args.lambda_name:
        print(f"Testing only the {args.lambda_name} Lambda function")
    
    exit_code = run_tests(args)
    
    # Print summary
    if exit_code == 0:
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed! See report above.")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 