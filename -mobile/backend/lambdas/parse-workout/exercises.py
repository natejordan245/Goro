"""
Module containing the list of known exercises for the workout parser.
This list is used to standardize exercise names and provide fuzzy matching.
NOTES FOR AI MODELS:
include bodyweight workouts in the catagory with the muscle worked in order to avoid duplicate entries.
"""

KNOWN_EXERCISES = {
    # Upper Body - Push
    "bench press",
    "incline bench press",
    "decline bench press",
    "overhead press",
    "push press",
    "dumbbell press",
    "dumbbell fly",
    "tricep extension",
    "tricep pushdown",
    "diamond pushup",
    "dip",
    
    # Upper Body - Pull
    "pull up",
    "chin up",
    "lat pulldown",
    "row",
    "barbell row",
    "dumbbell row",
    "face pull",
    "curl",
    "hammer curl",
    "preacher curl",
    
    # Lower Body
    "squat",
    "front squat",
    "back squat",
    "deadlift",
    "romanian deadlift",
    "sumo deadlift",
    "leg press",
    "leg extension",
    "leg curl",
    "calf raise",
    
    # Core
    "plank",
    "sit up",
    "crunch",
    "russian twist",
    "leg raise",
    
    # Cardio
    "run",
    "jog",
    "sprint",
    "bike",
    "swim",
    
    # Bodyweight
    "pushup",
    "pullup",
    "dip",
    "lunge",
    "burpee"
}