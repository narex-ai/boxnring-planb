"""
Dependencies for API endpoints.
"""
from fastapi import Request
from typing import Dict, Any, List
import random

import logging

logger = logging.getLogger(__name__)


def _shuffle(lst):
    lst_copy = lst[:]
    random.shuffle(lst_copy)
    return lst_copy

def _format_respond(llm_output: str, template: List) -> str:
    output = []
    arr = llm_output.split("\n")
    # Filter out empty strings from splitting
    arr = [line.strip() for line in arr if line.strip()]
    
    if len(arr) == len(template) * 2:
        dynamic = [
            {
                "question": arr[i],
                "whisper": arr[i + 1]
            }
            for i in range(0, len(arr), 2)
        ]
    elif len(arr) == len(template):
        dynamic = [
            {
                "question": arr[i],
                "whisper": template[i]['whisper']
            }
            for i in range(0, len(arr))
        ]
    else:
        # Handle unexpected output format
        logger.warning(
            f"Unexpected LLM output format. Expected {len(template)} or {len(template) * 2} lines, "
            f"got {len(arr)}. Using first {min(len(arr), len(template))} items as questions."
        )
        # Use available items, pad with template values if needed
        dynamic = []
        for i in range(len(template)):
            dynamic.append({
                "question": template[i].get('question', ''),
                "whisper": template[i].get('whisper', '')
            })

    animations = ["thinking", "nod", "celebration", "sad", "idle"]

    for index, item in enumerate(template):

        # Same logic as JS
        if item.get("interaction_pattern") == "complex":
            item["custom_input"] = True

        item["question_number"] = index + 1
        item["glovy_animation"] = animations[random.randint(0, 4)]

        item["question"] = dynamic[index]["question"]
        item["whisper"] = dynamic[index]["whisper"]

        output.append(item)

    # Final output
    return output

def get_app_state(request: Request) -> Dict[str, Any]:
    """Get application state from FastAPI app instance."""
    app = request.app
    return {
        "supabase_client": getattr(app.state, "supabase_client", None),
        "message_processor": getattr(app.state, "message_processor", None),
        "subscription": getattr(app.state, "subscription", None),
        "running": getattr(app.state, "running", False)
    }


def get_initiator_onboarding() -> List[Dict[str, Any]]:
    """
    Generate template data for spar initiator onboarding.
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
    
    template.append({
        "question":"What's the subject of this discussion?",
        "choices": [],
        "glovey_animation": "thinking",
        "whisper": "Describe the issue to your partner.👌",
        "interaction_pattern": "complex",
        "custom_input": True,
        "question_number": 4
    })

    return template


def get_invitee_onboarding() -> List[Dict[str, Any]]:
    """
    Generate template data for spar invitee onboarding.
    """
    template = [
    {
        "question": "How are you feeling before we begin?",
        "choices": _shuffle(random.choice([
            [
                {"label": "Calm and ready", "icon": "Smile", "value": "calm_ready"},
                {"label": "A bit nervous", "icon": "Wind", "value": "nervous"},
                {"label": "Curious to listen", "icon": "Eye", "value": "curious_listen"},
                {"label": "Excited to connect", "icon": "Sparkles", "value": "excited_connect"},
            ],
            [
                {"label": "Calm and ready", "icon": "Smile", "value": "calm_ready"},
                {"label": "A little nervous", "icon": "Wind", "value": "nervous"},
                {"label": "Curious to understand", "icon": "Eye", "value": "curious_understand"},
                {"label": "Excited to connect", "icon": "Sparkles", "value": "excited_connect"},
            ],
            [
                {"label": "Ready to talk", "icon": "Smile", "value": "ready_to_talk"},
                {"label": "A little anxious", "icon": "Wind", "value": "anxious"},
                {"label": "Want to understand", "icon": "Eye", "value": "want_to_understand"},
                {"label": "Hopeful to connect", "icon": "Sparkles", "value": "hopeful"},
            ],
            [
                {"label": "Ready to talk", "icon": "Smile", "value": "ready"},
                {"label": "A little nervous", "icon": "Wind", "value": "nervous"},
                {"label": "Want to understand", "icon": "Ear", "value": "want_to_understand"},
            ],
        ])),
        "whisper": "Select the option that best matches your mood 🌿",
        "interaction_pattern": "simple",
        "question_id": "invitee_emotion",
    },
    {
        "question": "What’s your main goal for this conversation?",
        "choices": _shuffle(random.choice([
            [
                {"label": "Listen and understand my partner", "icon": "Ear", "value": "listen_understand_partner"},
                {"label": "Find a solution together", "icon": "Handshake", "value": "find_solution_together"},
                {"label": "Reconnect emotionally", "icon": "HeartHandshake", "value": "reconnect_emotionally"},
                {"label": "Share my perspective", "icon": "MessageCircle", "value": "share_perspective"},
            ],
            [
                {"label": "Truly listen and understand", "icon": "Ear", "value": "truly_listen"},
                {"label": "Work toward a solution", "icon": "Handshake", "value": "work_solution"},
                {"label": "Reconnect and feel closer", "icon": "HeartHandshake", "value": "reconnect_closer"},
                {"label": "Share my thoughts and feelings", "icon": "MessageCircle", "value": "share_thoughts"},
            ],
            [
                {"label": "Listen and understand", "icon": "Ear", "value": "listen_understand"},
                {"label": "Find a solution", "icon": "Handshake", "value": "find_solution"},
                {"label": "Feel closer", "icon": "HeartHandshake", "value": "feel_closer"},
                {"label": "Share my perspective", "icon": "MessageCircle", "value": "share_perspective"},
            ],
            [
                {"label": "Listen and understand", "icon": "Ear", "value": "listen_understand"},
                {"label": "Find a solution", "icon": "Handshake", "value": "solution"},
                {"label": "Feel closer", "icon": "Heart", "value": "feel_closer"},
            ],
        ])),
        "whisper": "Pick the goal that feels most important to you right now 💛",
        "interaction_pattern": "simple",
        "question_number": 2,
        "question_id": "invitee_goal",
        },
    ]
    # Shuffle final list (equivalent to sort with random comparator)
    random.shuffle(template)

    # Return or print template
    return template


def get_visitor_onboarding() -> List[Dict[str, Any]]:

    template = [
        {
            "question": "What's the main goal you two have right now?",
            "choices": random.sample(
                    random.choice([
                        [
                            { "label": "Better communication", "icon": "MessageCircle", "value": "better_communication" },
                            { "label": "Reduce arguments", "icon": "Wind", "value": "reduce_arguments" },
                            { "label": "Learn conflict resolution", "icon": "Shield", "value": "learn_conflict_resolution" },
                            { "label": "Strengthen our bond", "icon": "Heart", "value": "strengthen_bond" },
                            { "label": "Prepare for marriage", "icon": "Calendar", "value": "prepare_marriage" },
                            { "label": "Work through specific issues", "icon": "Edit", "value": "specific_issues" },
                            { "label": "Build trust", "icon": "Users", "value": "build_trust" },
                            { "label": "Improve intimacy", "icon": "HeartHandshake", "value": "improve_intimacy" },
                            { "label": "Other (type your own)", "icon": "Edit", "value": "other" }
                        ],
                        [
                            { "label": "Communicate more clearly", "icon": "MessageCircle", "value": "communicate_clearly" },
                            { "label": "Argue with more respect", "icon": "Hand", "value": "reduce_conflict" },
                            { "label": "Feel closer emotionally", "icon": "Heart", "value": "feel_closer" },
                            { "label": "Build trust and stability", "icon": "Shield", "value": "build_trust" },
                            { "label": "Improve intimacy", "icon": "Sparkles", "value": "improve_intimacy" },
                            { "label": "Work on a specific issue", "icon": "Target", "value": "specific_issue" }
                        ],
                        [
                            { "label": "Better communication", "icon": "MessageCircle", "value": "better_communication" },
                            { "label": "Reduce arguments", "icon": "Minus", "value": "reduce_arguments" },
                            { "label": "Strengthen emotional closeness", "icon": "Heart", "value": "strengthen_closeness" },
                            { "label": "Build trust", "icon": "Shield", "value": "build_trust" },
                            { "label": "Improve intimacy", "icon": "Sparkles", "value": "improve_intimacy" },
                            { "label": "Work through a specific issue", "icon": "Target", "value": "specific_issue" }
                        ],
                        [
                            { "label": "Communicate more openly", "icon": "MessageCircle", "value": "communicate_openly" },
                            { "label": "Handle conflicts more gently", "icon": "Hand", "value": "gentler_conflict" },
                            { "label": "Feel more emotionally connected", "icon": "Heart", "value": "emotional_connection" },
                            { "label": "Build trust and safety", "icon": "Shield", "value": "trust_and_safety" },
                            { "label": "Deepen intimacy", "icon": "Sparkles", "value": "deepen_intimacy" },
                            { "label": "Focus on a specific ongoing issue", "icon": "Target", "value": "focus_specific_issue" }
                        ],
                        [
                            { "label": "Improve communication", "icon": "MessageCircle", "value": "improve_communication" },
                            { "label": "Reduce conflicts", "icon": "Wind", "value": "reduce_conflicts" },
                            { "label": "Strengthen emotional bond", "icon": "HeartHandshake", "value": "strengthen_bond" },
                            { "label": "Build trust", "icon": "Shield", "value": "build_trust" },
                            { "label": "Enhance intimacy", "icon": "Sparkles", "value": "enhance_intimacy" },
                            { "label": "Work through a specific issue", "icon": "Target", "value": "specific_issue" }
                        ]
                    ]),
                k=random.choice([4, 5, 6])
            ),
            "interaction_pattern": "complex",
            "question_id": "relationship_goal",
            "whisper": "No pressure — just pick the vibe 💛"
        },
        {
            "question": "How would you describe your relationship right now?",
            "choices": random.sample(
                    random.choice([
                        [
                            { "label": "Dating", "icon": "Users", "value": "dating" },
                            { "label": "Engaged", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Long-term partners", "icon": "Handshake", "value": "long_term_partners" }
                        ],
                        [
                            { "label": "Just dating", "icon": "Users", "value": "dating" },
                            { "label": "Engaged to be married", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Long-term committed partners", "icon": "Handshake", "value": "long_term_partners" }
                        ],
                        [
                            { "label": "Just dating", "icon": "Users", "value": "dating" },
                            { "label": "Planning to marry", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Committed long-term partners", "icon": "Handshake", "value": "long_term_partners" }
                        ],
                        [
                            { "label": "Dating casually", "icon": "Users", "value": "dating" },
                            { "label": "Engaged to be married", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Long-term committed partners", "icon": "Handshake", "value": "long_term_partners" }
                        ]
                    ]),
                k=4
            ),
            "interaction_pattern": random.choice(["simple", "complex", "simple"]),
            "question_id": "relationship_type",
            "whisper": "No pressure — just pick the vibe 💛"
        },
         {
            "question": "When conflict pops up, how do you tend to respond?",
            "choices": random.sample(
                    random.choice([
                    [
                        { "label": "Duck and weave", "icon": "Wind", "value": "avoiding" },
                        { "label": "Roll with it", "icon": "Smile", "value": "accommodating" },
                        { "label": "Throw back hard", "icon": "Frown", "value": "competing" },
                        { "label": "Meet in the middle", "icon": "Users", "value": "compromising" },
                        { "label": "Team up", "icon": "HeartHandshake", "value": "collaborating" }
                    ],[
                        { "label": "I step back and cool off", "icon": "Wind", "value": "avoiding" },
                        { "label": "I give in to keep the peace", "icon": "Handshake", "value": "accommodating" },
                        { "label": "I fight to win my point", "icon": "Shield", "value": "competing" },
                        { "label": "I try to find a quick compromise", "icon": "Users", "value": "compromising" },
                        { "label": "I work together to solve it", "icon": "HeartHandshake", "value": "collaborating" }
                    ], [
                        { "label": "Step back and cool off", "icon": "Wind", "value": "avoiding" },
                        { "label": "Give in to keep the peace", "icon": "Handshake", "value": "accommodating" },
                        { "label": "Fight to win", "icon": "Shield", "value": "competing" },
                        { "label": "Meet in the middle", "icon": "Users", "value": "compromising" },
                        { "label": "Work together to solve it", "icon": "HeartHandshake", "value": "collaborating" }
                    ],[
                        { "label": "I avoid confrontation and cool off", "icon": "Wind", "value": "avoiding" },
                        { "label": "I give way to keep harmony", "icon": "Handshake", "value": "accommodating" },
                        { "label": "I stand firm and argue my point", "icon": "Shield", "value": "competing" },
                        { "label": "I negotiate to find a fair compromise", "icon": "Users", "value": "compromising" },
                        { "label": "I collaborate to solve the issue together", "icon": "HeartHandshake", "value": "collaborating" }
                    ], [
                        { "label": "I step aside and let things cool", "icon": "Wind", "value": "avoiding" },
                        { "label": "I accommodate to keep the peace", "icon": "Handshake", "value": "accommodating" },
                        { "label": "I assert my point strongly", "icon": "Shield", "value": "competing" },
                        { "label": "I aim for a balanced compromise", "icon": "Users", "value": "compromising" },
                        { "label": "I collaborate to find a solution together", "icon": "HeartHandshake", "value": "collaborating" }
                    ]
                ]),
                k=random.choice([4,5])
            ),
            "whisper": "Go with the one that feels *most* like you 🥣",
            "interaction_pattern": random.choice(["simple", "complex", "simple", "simple"]),
            "question_id": "conflict_style"
        },
        {
            "question": "What tends to spark disagreements most often?",
            "choices": random.sample(
                random.choice([[
                    { "label": "Money matters", "icon": "DollarSign", "value": "money" },
                    { "label": "Scheduling and time stress", "icon": "Clock", "value": "time" },
                    { "label": "Household chores", "icon": "Calendar", "value": "chores" },
                    { "label": "Communication challenges", "icon": "MessageCircle", "value": "communication" },
                    { "label": "Family or relatives", "icon": "Users", "value": "family" },
                    { "label": "Work or career stress", "icon": "Briefcase", "value": "work" },
                    { "label": "Intimacy or closeness", "icon": "HeartHandshake", "value": "intimacy" }
                ],[
                    { "label": "Financial decisions", "icon": "DollarSign", "value": "finance" },
                    { "label": "Time and priorities", "icon": "Clock", "value": "time_priorities" },
                    { "label": "Division of chores", "icon": "Calendar", "value": "chores_division" },
                    { "label": "Communication misunderstandings", "icon": "MessageCircle", "value": "communication_misunderstanding" },
                    { "label": "Family obligations", "icon": "Users", "value": "family_obligations" },
                    { "label": "Work or career balance", "icon": "Briefcase", "value": "work_balance" },
                    { "label": "Emotional or physical closeness", "icon": "HeartHandshake", "value": "intimacy_issues" }
                ],[
                    { "label": "Money and spending", "icon": "DollarSign", "value": "money_spending" },
                    { "label": "Time management and schedules", "icon": "Clock", "value": "time_management" },
                    { "label": "Household responsibilities", "icon": "Calendar", "value": "household_responsibilities" },
                    { "label": "How we communicate", "icon": "MessageCircle", "value": "communication_style" },
                    { "label": "Family or relatives", "icon": "Users", "value": "family_issues" },
                    { "label": "Work or career demands", "icon": "Briefcase", "value": "work_demands" },
                    { "label": "Physical or emotional intimacy", "icon": "HeartHandshake", "value": "intimacy_issues" }
                ], [
                    { "label": "Financial choices", "icon": "DollarSign", "value": "financial_choices" },
                    { "label": "Time and daily routines", "icon": "Clock", "value": "time_routines" },
                    { "label": "Sharing household tasks", "icon": "Calendar", "value": "household_tasks" },
                    { "label": "Communication habits", "icon": "MessageCircle", "value": "communication_habits" },
                    { "label": "Family matters", "icon": "Users", "value": "family_matters" },
                    { "label": "Career or work stress", "icon": "Briefcase", "value": "career_stress" },
                    { "label": "Emotional or physical closeness", "icon": "HeartHandshake", "value": "closeness_issues" },
                ]
                ]),
                k=random.choice([4,5,6])
            ),
            "interaction_pattern": random.choice(["simple", "complex", "complex", "complex"]),
            "question_id": "conflict_trigger",
            "whisper": "Choose the one that matches what matters most right now 💛"
        },
        {
            "question": "How would you describe communication between you two lately?",
            "choices": _shuffle(
                random.choice([
                    [
                        { "label": "Struggle to be understood", "icon": "Frown", "value": "foggy" },
                        { "label": "Sometimes clear, sometimes confusing", "icon": "Wind", "value": "mixed" },
                        { "label": "Mostly clear with minor misunderstandings", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Open, honest, and constructive", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ], [
                        { "label": "Crystal Clear — We understand each other almost instantly.", "icon": "Sparkles", "value": "crystal_clear" },
                        { "label": "Mostly Clear — We get there, but sometimes need a second try.", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Mixed — Some topics are easy, others get tangled fast.", "icon": "Cloud", "value": "mixed" },
                        { "label": "Foggy — We try, but it often feels like we miss each other.", "icon": "Wind", "value": "foggy" }
                    ],[
                        { "label": "We often struggle to get through", "icon": "Frown", "value": "foggy" },
                        { "label": "Sometimes we work it out, sometimes not", "icon": "Wind", "value": "mixed" },
                        { "label": "Mostly smooth, but could improve", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Open and constructive most of the time", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ],[
                        { "label": "We often misunderstand each other", "icon": "Frown", "value": "foggy" },
                        { "label": "Some conflicts get resolved, some linger", "icon": "Wind", "value": "mixed" },
                        { "label": "Mostly clear, occasional hiccups", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Very open, respectful, and constructive", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ], [
                        { "label": "Often tense or unclear", "icon": "Frown", "value": "foggy" },
                        { "label": "Inconsistent — sometimes good, sometimes rough", "icon": "Wind", "value": "mixed" },
                        { "label": "Generally smooth with occasional bumps", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Clear, open, and respectful most of the time", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ]
                ])
            ),
            "interaction_pattern": "simple",
            "question_id": "communication_level",
            "whisper": "Just go with what it feels like most days 🏡"
        },
        {
            "question": "How long have you two been together?",
            "choices": random.choice([
                [
                    {"label": "New Love (<1 year)", "icon": "Sparkles", "value": "0_1_year"},
                    {"label": "Growing Strong (1–2 years)", "icon": "Heart", "value": "1_2_years"},
                    {"label": "Deep Roots (3–5 years)", "icon": "TreePine", "value": "3_5_years"},
                    {"label": "Mountain High (6–10 years)", "icon": "Home", "value": "6_10_years"},
                    {"label": "Diamond Strong (10+ years)", "icon": "Diamond", "value": "10_plus_years"},
                ],
                [
                    {"label": "Just Started (<1 year)", "icon": "Sparkles", "value": "0_1_year"},
                    {"label": "Finding Our Rhythm (1–2 years)", "icon": "Heart", "value": "1_2_years"},
                    {"label": "Strong Bond (3–5 years)", "icon": "TreePine", "value": "3_5_years"},
                    {"label": "Established Connection (6–10 years)", "icon": "Mountain", "value": "6_10_years"},
                    {"label": "Lifetime Together (10+ years)", "icon": "Diamond", "value": "10_plus_years"},
                ],
                [
                    {"label": "Under 2 years", "icon": "Sparkles", "value": "0_2_years"},
                    {"label": "3–5 years", "icon": "TreePine", "value": "3_5_years"},
                    {"label": "6+ years", "icon": "Diamond", "value": "6_plus_years"},
                ]
            ]),
            "interaction_pattern": "simple",
            "question_id": "relationship_duration",
            "whisper": "Time flies when you're building something 💍"
        }
    ]

    template = random.sample(template, k=random.choice([3, 4, 5]))
    template.append({
        "question": "Want to invite your partner to join you?",
        "choices": [
            { "label": "Yes - Send invite", "icon": "Send", "value": "invite_now" },
            { "label": "I'll do it later", "icon": "Clock", "value": "invite_later" }
        ],
        "glovey_animation": "celebration",
        "whisper": "You're doing great!🥳",
        "interaction_pattern": "critical",
        "question_number": len(template) + 1,
        "is_final": True
    })
    return template



def get_partner_onboarding() -> List[Dict[str, Any]]:

    template = [
        {
            "question": "What's the main goal you two have right now?",
            "choices": random.sample(
                    random.choice([
                        [
                            { "label": "Better communication", "icon": "MessageCircle", "value": "better_communication" },
                            { "label": "Reduce arguments", "icon": "Wind", "value": "reduce_arguments" },
                            { "label": "Learn conflict resolution", "icon": "Shield", "value": "learn_conflict_resolution" },
                            { "label": "Strengthen our bond", "icon": "Heart", "value": "strengthen_bond" },
                            { "label": "Prepare for marriage", "icon": "Calendar", "value": "prepare_marriage" },
                            { "label": "Work through specific issues", "icon": "Edit", "value": "specific_issues" },
                            { "label": "Build trust", "icon": "Users", "value": "build_trust" },
                            { "label": "Improve intimacy", "icon": "HeartHandshake", "value": "improve_intimacy" },
                            { "label": "Other (type your own)", "icon": "Edit", "value": "other" }
                        ],
                        [
                            { "label": "Communicate more clearly", "icon": "MessageCircle", "value": "communicate_clearly" },
                            { "label": "Argue with more respect", "icon": "Hand", "value": "reduce_conflict" },
                            { "label": "Feel closer emotionally", "icon": "Heart", "value": "feel_closer" },
                            { "label": "Build trust and stability", "icon": "Shield", "value": "build_trust" },
                            { "label": "Improve intimacy", "icon": "Sparkles", "value": "improve_intimacy" },
                            { "label": "Work on a specific issue", "icon": "Target", "value": "specific_issue" }
                        ],
                        [
                            { "label": "Better communication", "icon": "MessageCircle", "value": "better_communication" },
                            { "label": "Reduce arguments", "icon": "Minus", "value": "reduce_arguments" },
                            { "label": "Strengthen emotional closeness", "icon": "Heart", "value": "strengthen_closeness" },
                            { "label": "Build trust", "icon": "Shield", "value": "build_trust" },
                            { "label": "Improve intimacy", "icon": "Sparkles", "value": "improve_intimacy" },
                            { "label": "Work through a specific issue", "icon": "Target", "value": "specific_issue" }
                        ],
                        [
                            { "label": "Communicate more openly", "icon": "MessageCircle", "value": "communicate_openly" },
                            { "label": "Handle conflicts more gently", "icon": "Hand", "value": "gentler_conflict" },
                            { "label": "Feel more emotionally connected", "icon": "Heart", "value": "emotional_connection" },
                            { "label": "Build trust and safety", "icon": "Shield", "value": "trust_and_safety" },
                            { "label": "Deepen intimacy", "icon": "Sparkles", "value": "deepen_intimacy" },
                            { "label": "Focus on a specific ongoing issue", "icon": "Target", "value": "focus_specific_issue" }
                        ],
                        [
                            { "label": "Improve communication", "icon": "MessageCircle", "value": "improve_communication" },
                            { "label": "Reduce conflicts", "icon": "Wind", "value": "reduce_conflicts" },
                            { "label": "Strengthen emotional bond", "icon": "HeartHandshake", "value": "strengthen_bond" },
                            { "label": "Build trust", "icon": "Shield", "value": "build_trust" },
                            { "label": "Enhance intimacy", "icon": "Sparkles", "value": "enhance_intimacy" },
                            { "label": "Work through a specific issue", "icon": "Target", "value": "specific_issue" }
                        ]
                    ]),
                k=random.choice([4, 5, 6])
            ),
            "interaction_pattern": "complex",
            "question_id": "relationship_goal",
            "whisper": "No pressure — just pick the vibe 💛"
        },
        {
            "question": "How would you describe your relationship right now?",
            "choices": random.sample(
                    random.choice([
                        [
                            { "label": "Dating", "icon": "Users", "value": "dating" },
                            { "label": "Engaged", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Long-term partners", "icon": "Handshake", "value": "long_term_partners" }
                        ],
                        [
                            { "label": "Just dating", "icon": "Users", "value": "dating" },
                            { "label": "Engaged to be married", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Long-term committed partners", "icon": "Handshake", "value": "long_term_partners" }
                        ],
                        [
                            { "label": "Just dating", "icon": "Users", "value": "dating" },
                            { "label": "Planning to marry", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Committed long-term partners", "icon": "Handshake", "value": "long_term_partners" }
                        ],
                        [
                            { "label": "Dating casually", "icon": "Users", "value": "dating" },
                            { "label": "Engaged to be married", "icon": "HeartHandshake", "value": "engaged" },
                            { "label": "Married", "icon": "Heart", "value": "married" },
                            { "label": "Long-term committed partners", "icon": "Handshake", "value": "long_term_partners" }
                        ]
                    ]),
                k=4
            ),
            "interaction_pattern": random.choice(["simple", "complex", "simple"]),
            "question_id": "relationship_type",
            "whisper": "No pressure — just pick the vibe 💛"
        },
         {
            "question": "When conflict pops up, how do you tend to respond?",
            "choices": random.sample(
                    random.choice([
                    [
                        { "label": "Duck and weave", "icon": "Wind", "value": "avoiding" },
                        { "label": "Roll with it", "icon": "Smile", "value": "accommodating" },
                        { "label": "Throw back hard", "icon": "Frown", "value": "competing" },
                        { "label": "Meet in the middle", "icon": "Users", "value": "compromising" },
                        { "label": "Team up", "icon": "HeartHandshake", "value": "collaborating" }
                    ],[
                        { "label": "I step back and cool off", "icon": "Wind", "value": "avoiding" },
                        { "label": "I give in to keep the peace", "icon": "Handshake", "value": "accommodating" },
                        { "label": "I fight to win my point", "icon": "Shield", "value": "competing" },
                        { "label": "I try to find a quick compromise", "icon": "Users", "value": "compromising" },
                        { "label": "I work together to solve it", "icon": "HeartHandshake", "value": "collaborating" }
                    ], [
                        { "label": "Step back and cool off", "icon": "Wind", "value": "avoiding" },
                        { "label": "Give in to keep the peace", "icon": "Handshake", "value": "accommodating" },
                        { "label": "Fight to win", "icon": "Shield", "value": "competing" },
                        { "label": "Meet in the middle", "icon": "Users", "value": "compromising" },
                        { "label": "Work together to solve it", "icon": "HeartHandshake", "value": "collaborating" }
                    ],[
                        { "label": "I avoid confrontation and cool off", "icon": "Wind", "value": "avoiding" },
                        { "label": "I give way to keep harmony", "icon": "Handshake", "value": "accommodating" },
                        { "label": "I stand firm and argue my point", "icon": "Shield", "value": "competing" },
                        { "label": "I negotiate to find a fair compromise", "icon": "Users", "value": "compromising" },
                        { "label": "I collaborate to solve the issue together", "icon": "HeartHandshake", "value": "collaborating" }
                    ], [
                        { "label": "I step aside and let things cool", "icon": "Wind", "value": "avoiding" },
                        { "label": "I accommodate to keep the peace", "icon": "Handshake", "value": "accommodating" },
                        { "label": "I assert my point strongly", "icon": "Shield", "value": "competing" },
                        { "label": "I aim for a balanced compromise", "icon": "Users", "value": "compromising" },
                        { "label": "I collaborate to find a solution together", "icon": "HeartHandshake", "value": "collaborating" }
                    ]
                ]),
                k=random.choice([4,5])
            ),
            "whisper": "Go with the one that feels *most* like you 🥣",
            "interaction_pattern": random.choice(["simple", "complex", "simple", "simple"]),
            "question_id": "conflict_style"
        },
        {
            "question": "What tends to spark disagreements most often?",
            "choices": random.sample(
                random.choice([[
                    { "label": "Money matters", "icon": "DollarSign", "value": "money" },
                    { "label": "Scheduling and time stress", "icon": "Clock", "value": "time" },
                    { "label": "Household chores", "icon": "Calendar", "value": "chores" },
                    { "label": "Communication challenges", "icon": "MessageCircle", "value": "communication" },
                    { "label": "Family or relatives", "icon": "Users", "value": "family" },
                    { "label": "Work or career stress", "icon": "Briefcase", "value": "work" },
                    { "label": "Intimacy or closeness", "icon": "HeartHandshake", "value": "intimacy" }
                ],[
                    { "label": "Financial decisions", "icon": "DollarSign", "value": "finance" },
                    { "label": "Time and priorities", "icon": "Clock", "value": "time_priorities" },
                    { "label": "Division of chores", "icon": "Calendar", "value": "chores_division" },
                    { "label": "Communication misunderstandings", "icon": "MessageCircle", "value": "communication_misunderstanding" },
                    { "label": "Family obligations", "icon": "Users", "value": "family_obligations" },
                    { "label": "Work or career balance", "icon": "Briefcase", "value": "work_balance" },
                    { "label": "Emotional or physical closeness", "icon": "HeartHandshake", "value": "intimacy_issues" }
                ],[
                    { "label": "Money and spending", "icon": "DollarSign", "value": "money_spending" },
                    { "label": "Time management and schedules", "icon": "Clock", "value": "time_management" },
                    { "label": "Household responsibilities", "icon": "Calendar", "value": "household_responsibilities" },
                    { "label": "How we communicate", "icon": "MessageCircle", "value": "communication_style" },
                    { "label": "Family or relatives", "icon": "Users", "value": "family_issues" },
                    { "label": "Work or career demands", "icon": "Briefcase", "value": "work_demands" },
                    { "label": "Physical or emotional intimacy", "icon": "HeartHandshake", "value": "intimacy_issues" }
                ], [
                    { "label": "Financial choices", "icon": "DollarSign", "value": "financial_choices" },
                    { "label": "Time and daily routines", "icon": "Clock", "value": "time_routines" },
                    { "label": "Sharing household tasks", "icon": "Calendar", "value": "household_tasks" },
                    { "label": "Communication habits", "icon": "MessageCircle", "value": "communication_habits" },
                    { "label": "Family matters", "icon": "Users", "value": "family_matters" },
                    { "label": "Career or work stress", "icon": "Briefcase", "value": "career_stress" },
                    { "label": "Emotional or physical closeness", "icon": "HeartHandshake", "value": "closeness_issues" },
                ]
                ]),
                k=random.choice([4,5,6])
            ),
            "interaction_pattern": random.choice(["simple", "complex", "complex", "complex"]),
            "question_id": "conflict_trigger",
            "whisper": "Choose the one that matches what matters most right now 💛"
        },
        {
            "question": "How would you describe communication between you two lately?",
            "choices": _shuffle(
                random.choice([
                    [
                        { "label": "Struggle to be understood", "icon": "Frown", "value": "foggy" },
                        { "label": "Sometimes clear, sometimes confusing", "icon": "Wind", "value": "mixed" },
                        { "label": "Mostly clear with minor misunderstandings", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Open, honest, and constructive", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ], [
                        { "label": "Crystal Clear — We understand each other almost instantly.", "icon": "Sparkles", "value": "crystal_clear" },
                        { "label": "Mostly Clear — We get there, but sometimes need a second try.", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Mixed — Some topics are easy, others get tangled fast.", "icon": "Cloud", "value": "mixed" },
                        { "label": "Foggy — We try, but it often feels like we miss each other.", "icon": "Wind", "value": "foggy" }
                    ],[
                        { "label": "We often struggle to get through", "icon": "Frown", "value": "foggy" },
                        { "label": "Sometimes we work it out, sometimes not", "icon": "Wind", "value": "mixed" },
                        { "label": "Mostly smooth, but could improve", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Open and constructive most of the time", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ],[
                        { "label": "We often misunderstand each other", "icon": "Frown", "value": "foggy" },
                        { "label": "Some conflicts get resolved, some linger", "icon": "Wind", "value": "mixed" },
                        { "label": "Mostly clear, occasional hiccups", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Very open, respectful, and constructive", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ], [
                        { "label": "Often tense or unclear", "icon": "Frown", "value": "foggy" },
                        { "label": "Inconsistent — sometimes good, sometimes rough", "icon": "Wind", "value": "mixed" },
                        { "label": "Generally smooth with occasional bumps", "icon": "Smile", "value": "mostly_clear" },
                        { "label": "Clear, open, and respectful most of the time", "icon": "HeartHandshake", "value": "crystal_clear" }
                    ]
                ])
            ),
            "interaction_pattern": "simple",
            "question_id": "communication_level",
            "whisper": "Just go with what it feels like most days 🏡"
        },
        {
            "question": "How long have you two been together?",
            "choices": random.choice([
                [
                    {"label": "New Love (<1 year)", "icon": "Sparkles", "value": "0_1_year"},
                    {"label": "Growing Strong (1–2 years)", "icon": "Heart", "value": "1_2_years"},
                    {"label": "Deep Roots (3–5 years)", "icon": "TreePine", "value": "3_5_years"},
                    {"label": "Mountain High (6–10 years)", "icon": "Home", "value": "6_10_years"},
                    {"label": "Diamond Strong (10+ years)", "icon": "Diamond", "value": "10_plus_years"},
                ],
                [
                    {"label": "Just Started (<1 year)", "icon": "Sparkles", "value": "0_1_year"},
                    {"label": "Finding Our Rhythm (1–2 years)", "icon": "Heart", "value": "1_2_years"},
                    {"label": "Strong Bond (3–5 years)", "icon": "TreePine", "value": "3_5_years"},
                    {"label": "Established Connection (6–10 years)", "icon": "Mountain", "value": "6_10_years"},
                    {"label": "Lifetime Together (10+ years)", "icon": "Diamond", "value": "10_plus_years"},
                ],
                [
                    {"label": "Under 2 years", "icon": "Sparkles", "value": "0_2_years"},
                    {"label": "3–5 years", "icon": "TreePine", "value": "3_5_years"},
                    {"label": "6+ years", "icon": "Diamond", "value": "6_plus_years"},
                ]
            ]),
            "interaction_pattern": "simple",
            "question_id": "relationship_duration",
            "whisper": "Time flies when you're building something 💍"
        }
    ]

    template = random.sample(template, k=2)
    return template
