from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# =============================================
# CONFIGURATION
# =============================================
GEMINI_API_KEY = "AIzaSyAqW1OnDmpBt_CiK7FUhU-AR7OhZus7EWI"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

app = FastAPI(title="AI Mock Interviewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# MODELS
# =============================================
class FeedbackRequest(BaseModel):
    transcript: str
    question: str
    session_id: str

# =============================================
# ROUTES
# =============================================
@app.get("/")
def home():
    return {"message": "AI Mock Interviewer API is running!"}


@app.get("/questions/{category}")
def get_questions(category: str):
    questions = {
        "behavioural": [
            "Tell me about yourself.",
            "What is your greatest weakness?",
            "Describe a time when you worked in a team.",
            "How do you handle pressure and deadlines?",
            "Where do you see yourself in 5 years?",
            "Tell me about a challenge you overcame.",
            "Why should we hire you?",
            "What motivates you?"
        ],
        "technical": [
            "What is Object-Oriented Programming?",
            "Explain the difference between SQL and NoSQL.",
            "What is a REST API?",
            "Explain time complexity in algorithms.",
            "What is version control and why is it important?",
            "Explain the concept of recursion.",
            "What is a design pattern? Name a few.",
            "How does a database index work?"
        ]
    }
    category = category.lower()
    if category not in questions:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"questions": questions[category], "category": category}


@app.post("/analyze")
async def analyze(request: FeedbackRequest):
    transcript = request.transcript
    question = request.question
    words = transcript.lower().split()

    # ---- Filler Word Detection ----
    fillers = ["um", "uh", "ah", "like", "basically", "literally"]
    found = {f: words.count(f) for f in fillers if words.count(f) > 0}
    total_fillers = sum(found.values())

    # ---- Basic Score Calculation ----
    score = 70
    if total_fillers == 0:
        score += 20
    elif total_fillers <= 3:
        score += 10
    elif total_fillers > 7:
        score -= 20

    word_count = len(words)
    if 50 <= word_count <= 200:
        score += 10
    elif word_count < 20:
        score -= 20

    score = max(0, min(100, score))

    # ---- Gemini AI Feedback ----
    try:
        prompt = f"""
You are an expert interview coach. Analyze this interview answer and give structured feedback.

Interview Question: {question}
Candidate's Answer: {transcript}
Confidence Score: {score}/100
Filler Words Used: {found if found else "None"}
Word Count: {word_count}

Give feedback in this EXACT JSON format (no extra text):
{{
    "overall_rating": "Excellent/Good/Needs Improvement",
    "summary": "2-3 sentence overall assessment",
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "improvements": ["improvement 1", "improvement 2", "improvement 3"],
    "better_answer_tip": "One specific tip to improve this answer",
    "star_method_suggestion": "How to structure this answer using STAR method"
}}
"""
        response = model.generate_content(prompt)
        import json
        raw = response.text.strip()
        # Clean markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        ai_feedback = json.loads(raw.strip())

    except Exception as e:
        # Fallback if Gemini fails
        ai_feedback = {
            "overall_rating": "Excellent" if score >= 80 else "Good" if score >= 60 else "Needs Improvement",
            "summary": "Your answer showed effort. Focus on reducing filler words and adding specific examples.",
            "strengths": ["Attempted the question", "Basic structure present"],
            "improvements": ["Reduce filler words", "Add specific examples", "Use STAR method"],
            "better_answer_tip": "Try to give a concrete example from your experience.",
            "star_method_suggestion": "Structure: Situation → Task → Action → Result"
        }

    return {
        "success": True,
        "transcript": transcript,
        "confidence_score": score,
        "fillers": {
            "found_fillers": found,
            "total_count": total_fillers,
            "severity": "Excellent" if total_fillers == 0 else "Good" if total_fillers <= 3 else "Needs Work"
        },
        "word_count": word_count,
        "feedback": ai_feedback
    }
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)