"""
Dependencies for API endpoints.
"""
from fastapi import Request
from typing import Dict, Any, List
import random

def get_app_state(request: Request) -> Dict[str, Any]:
    """Get application state from FastAPI app instance."""
    app = request.app
    return {
        "supabase_client": getattr(app.state, "supabase_client", None),
        "message_processor": getattr(app.state, "message_processor", None),
        "subscription": getattr(app.state, "subscription", None),
        "running": getattr(app.state, "running", False)
    }


def get_spar_onboarding() -> List[Dict[str, Any]]:
    """
    Generate template data for spar onboarding.
    Converts the JavaScript template function to Python.
    """
    # First question: How are you feeling right now?
    emotion_choices = [
        {"label": "😤 Frustrated", "icon": "Frown", "value": "frustrated"},
        {"label": "😢 Hurt", "icon": "HeartCrack", "value": "hurt"},
        {"label": "😕 Confused", "icon": "HelpCircle", "value": "confused"},
        {"label": "😄 Excited", "icon": "Smile", "value": "excited"},
        {"label": "😰 Nervous", "icon": "Wind", "value": "nervous"},
        {"label": "😠 Angry", "icon": "AlertTriangle", "value": "angry"},
        {"label": "😞 Sad", "icon": "Frown", "value": "sad"},
        {"label": "😊 Happy", "icon": "Smile", "value": "happy"},
        {"label": "😟 Anxious", "icon": "Clock", "value": "anxious"},
        {"label": "😌 Calm", "icon": "Wind", "value": "calm"},
        {"label": "🙂 Hopeful", "icon": "Sparkles", "value": "hopeful"},
        {"label": "😵 Overwhelmed", "icon": "AlertCircle", "value": "overwhelmed"}
    ]
    random.shuffle(emotion_choices)
    emotion_choices = emotion_choices[:5]
    
    question1 = {
        "question": "How are you feeling right now?",
        "choices": emotion_choices,
        "whisper": "Take a deep breath 🌿 and pick the one that fits your mood best.",
        "interaction_pattern": "simple",
        "question_id": "initiator_emotion"
    }
    
    # Second question: What's your goal for this conversation?
    goal_choices_variants = [
        [
            {"label": "Be heard and understood", "icon": "Ear", "value": "be_heard"},
            {"label": "Understand each other", "icon": "Users", "value": "understand_each_other"},
            {"label": "Reconnect and feel closer", "icon": "Heart", "value": "reconnect"},
            {"label": "Find a practical solution", "icon": "Handshake", "value": "find_solution"}
        ],
        [
            {"label": "Share my feelings", "icon": "MessageCircle", "value": "share_feelings"},
            {"label": "Listen and understand", "icon": "Ear", "value": "listen_understand"},
            {"label": "Feel more connected", "icon": "HeartHandshake", "value": "feel_connected"},
            {"label": "Resolve a specific issue", "icon": "Handshake", "value": "resolve_issue"}
        ],
        [
            {"label": "Be truly heard", "icon": "Ear", "value": "be_truly_heard"},
            {"label": "Understand my partner better", "icon": "Users", "value": "understand_partner"},
            {"label": "Reconnect emotionally", "icon": "HeartHandshake", "value": "reconnect_emotionally"},
            {"label": "Find a clear solution", "icon": "Handshake", "value": "find_solution"}
        ]
    ]
    
    # Select a random variant and shuffle it, then take first 4
    selected_goal_variant = random.choice(goal_choices_variants)
    random.shuffle(selected_goal_variant)
    goal_choices = selected_goal_variant[:4]
    
    question2 = {
        "question": "What's your goal for this conversation?",
        "choices": goal_choices,
        "whisper": "Pick what feels most important to you right now 🎯",
        "interaction_pattern": "simple",
        "question_id": "initiator_goal"
    }
    
    # Third question: What's the main topic you two want to talk about right now?
    topic_choices = [
        {"label": "Money", "icon": "DollarSign", "value": "money"},
        {"label": "Time & schedules", "icon": "Clock", "value": "time"},
        {"label": "Chores / responsibilities", "icon": "Calendar", "value": "chores"},
        {"label": "Communication style", "icon": "MessageCircle", "value": "communication"},
        {"label": "Family dynamics", "icon": "Users", "value": "family"},
        {"label": "Intimacy & closeness", "icon": "HeartHandshake", "value": "intimacy"}
    ]
    random.shuffle(topic_choices)
    topic_choices = topic_choices[:4]
    
    question3 = {
        "question": "What's the main topic you two want to talk about right now?",
        "choices": topic_choices,
        "interaction_pattern": "complex",
        "question_id": "topic_selection",
        "whisper": "Choose the one that matches what matters most right now 💛"
    }
    
    # Combine all questions and shuffle the order
    template = [question1, question2, question3]
    random.shuffle(template)
    
    return template
