"""
Prompt templates for question generation, evaluation, and feedback.
"""


def build_question_prompt(
    agent_type: str,
    candidate_profile: str,
    category: str = "",
    difficulty: str = "medium",
    previous_questions: list[str] | None = None,
    context: str = "",
) -> str:
    prev = ""
    if previous_questions:
        prev = "\n\nPrevious questions asked (DO NOT repeat):\n" + "\n".join(
            f"- {q}" for q in previous_questions
        )

    ctx = f"\n\nAdditional context:\n{context}" if context else ""

    return f"""Generate a {difficulty} difficulty {agent_type} interview question.

Candidate Profile:
{candidate_profile}

Category: {category or 'General'}
Difficulty: {difficulty}
{prev}{ctx}

Requirements:
- Make the question specific and clear
- Tailor to the candidate's experience level
- Focus on practical understanding, not just theory
- Include a brief note on what a good answer should cover

Respond with JSON:
{{
    "question": "Your interview question here",
    "category": "{category or 'General'}",
    "difficulty": "{difficulty}",
    "expected_topics": ["topic1", "topic2", "topic3"],
    "follow_up_hint": "A possible follow-up question"
}}"""


def build_evaluation_prompt(
    question: str,
    answer: str,
    agent_type: str,
    candidate_profile: str = "",
) -> str:
    return f"""Evaluate the following interview answer.

Question ({agent_type}):
{question}

Candidate's Answer:
{answer}

{f"Candidate Profile: {candidate_profile}" if candidate_profile else ""}

Score each dimension from 0 to 10:

Respond with JSON:
{{
    "technical_accuracy": <0-10>,
    "depth_of_understanding": <0-10>,
    "communication_clarity": <0-10>,
    "problem_solving": <0-10>,
    "code_quality": <0-10 or 0 if not applicable>,
    "reasoning": "Brief explanation of your scoring",
    "key_strengths": ["strength1", "strength2"],
    "areas_to_improve": ["area1", "area2"]
}}"""


def build_resume_parse_prompt(raw_text: str) -> str:
    return f"""Analyze the following resume text and extract structured information.

Resume Text:
{raw_text[:4000]}

Extract and return as JSON:
{{
    "candidate_name": "Full name",
    "email": "email if found",
    "phone": "phone if found",
    "skills": ["skill1", "skill2", ...],
    "technologies": ["tech1", "tech2", ...],
    "experience": [
        {{"title": "Job Title", "company": "Company", "duration": "X years", "description": "Brief desc"}}
    ],
    "education": [
        {{"degree": "Degree", "institution": "University", "year": "Year"}}
    ],
    "projects": [
        {{"name": "Project Name", "description": "Brief desc", "technologies": ["tech1"]}}
    ],
    "certifications": ["cert1", "cert2"],
    "summary": "2-3 sentence professional summary",
    "strengths": ["strength1", "strength2"],
    "gaps": ["gap1", "gap2"]
}}"""


def build_feedback_prompt(
    candidate_profile: str,
    questions_answers: list[dict],
    evaluations: list[dict],
) -> str:
    qa_text = ""
    for i, qa in enumerate(questions_answers, 1):
        qa_text += f"\nQ{i} [{qa.get('category', 'General')}]: {qa.get('question', '')}\n"
        qa_text += f"A{i}: {qa.get('answer', '')}\n"
        if i <= len(evaluations):
            ev = evaluations[i - 1]
            qa_text += f"Score: {ev.get('composite_score', 'N/A')}/10\n"

    return f"""Generate a comprehensive interview feedback report.

Candidate Profile:
{candidate_profile}

Interview Q&A with Scores:
{qa_text}

Generate a detailed JSON report:
{{
    "overall_score": <0-100>,
    "technical_score": <0-100>,
    "behavioral_score": <0-100>,
    "coding_score": <0-100>,
    "hiring_recommendation": "strong_hire|hire|maybe|no_hire",
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2"],
    "improvement_roadmap": {{
        "short_term": ["action1", "action2"],
        "medium_term": ["action3", "action4"],
        "long_term": ["action5"]
    }},
    "summary": "Executive summary paragraph",
    "detailed_feedback": "Comprehensive multi-paragraph feedback"
}}"""


def build_coding_evaluation_prompt(
    problem: str,
    code: str,
    language: str,
) -> str:
    return f"""Evaluate the following code solution.

Problem:
{problem}

Language: {language}
Solution:
```{language}
{code}
```

Evaluate and respond with JSON:
{{
    "correctness": <0-10>,
    "efficiency": <0-10>,
    "code_quality": <0-10>,
    "time_complexity": "O(...)",
    "space_complexity": "O(...)",
    "test_cases": [
        {{"input": "test input", "expected": "expected output", "passed": true}}
    ],
    "feedback": "Detailed feedback on the solution",
    "improvements": ["suggestion1", "suggestion2"]
}}"""
