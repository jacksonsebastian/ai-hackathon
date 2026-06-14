"""Evaluation-specific prompt templates."""

EVALUATION_RUBRIC = {
    "technical_accuracy": {
        "description": "Correctness of technical content and concepts",
        "weight": 0.30,
        "levels": {
            "0-2": "Fundamentally incorrect or irrelevant",
            "3-4": "Partially correct with significant errors",
            "5-6": "Mostly correct with minor gaps",
            "7-8": "Accurate with good depth",
            "9-10": "Excellent, comprehensive, and precise",
        },
    },
    "depth_of_understanding": {
        "description": "How deeply the candidate understands the topic",
        "weight": 0.25,
        "levels": {
            "0-2": "Surface-level or memorized response",
            "3-4": "Basic understanding, limited depth",
            "5-6": "Good understanding with some insight",
            "7-8": "Deep understanding with practical examples",
            "9-10": "Expert-level insight and nuanced understanding",
        },
    },
    "communication_clarity": {
        "description": "Clarity and structure of the response",
        "weight": 0.20,
        "levels": {
            "0-2": "Incoherent or very unclear",
            "3-4": "Somewhat clear but disorganized",
            "5-6": "Clear and reasonably structured",
            "7-8": "Well-structured with good examples",
            "9-10": "Exceptionally clear, concise, and well-organized",
        },
    },
    "problem_solving": {
        "description": "Approach to problem decomposition and solving",
        "weight": 0.15,
        "levels": {
            "0-2": "No clear approach",
            "3-4": "Basic approach with limited analysis",
            "5-6": "Reasonable approach with some analysis",
            "7-8": "Strong systematic approach",
            "9-10": "Exceptional problem-solving methodology",
        },
    },
    "code_quality": {
        "description": "Code cleanliness, efficiency, and best practices",
        "weight": 0.10,
        "levels": {
            "0-2": "Non-functional or very poor quality",
            "3-4": "Works but poor style and efficiency",
            "5-6": "Functional with acceptable quality",
            "7-8": "Clean, efficient, well-structured",
            "9-10": "Production-quality, optimal solution",
        },
    },
}

HIRING_CRITERIA = {
    "strong_hire": {"min_score": 80, "description": "Exceptional candidate, strongly recommended"},
    "hire": {"min_score": 65, "description": "Good candidate, recommended with minor development areas"},
    "maybe": {"min_score": 50, "description": "Borderline candidate, needs further evaluation"},
    "no_hire": {"min_score": 0, "description": "Does not meet requirements at this time"},
}
