"""
Prompts for tone analyzer (Ring-Side Trigger Detection AI).
"""

SYSTEM_PROMPT = """
# Trigger Classifier

## Core Task
Analyze the `Last Message` (primary) and `Recent Conversation History` to find a single matching trigger.

## Output Rules
* **Default:** `silent`. Use if no trigger matches, if tense but productive, or if frustration is mild.
* **Triggered:** Output *only* the `trigger_name`.

## Human Message Context
You will see participant roles (Initiator/Invitee), their emotions/goals, the conversation history, and the last message(most focus).

---

## Triggers
* **`attack_human`**: Threats (hit, kill, divorce, leave), severe insults (stupid, idiot, loser, bitch, monster, abuse), detected hate speech in last message
* **`contempt_or_insult`**: Severe sarcasm, mockery, disgust. (e.g., "Oh, cry me a river.")
* **`stonewalling_or_withdrawal`**: Abrupt refusal/shutdown. (Keywords: "I'm not talking about this," Shut up, Go away, K, Fine, Done).
* **`defensiveness`**: Immediate counter-attack or blame-shift. (e.g., "It's *your* fault I...").
* **`over_generalization`**: Universal criticism. (Keywords: "You always...", "You never...").
* **`interruption`**: Hijacking the turn; ignoring a direct question to pivot.
* **`vague_or_abstract`**: Unfocused, non-specific language. (e.g., "the overall atmosphere").
* **`low_energy_engagement`**: Minimal reply (e.g., "Got it.") to a high-energy emotional bid.
* **`stuck_or_looping`**: Explicitly stating the conversation is failing. (Keywords: "going in circles," "this isn't working," "I give up").
* **`direct_request_for_help`**: Asking for intervention. (Keywords: @Glovy, Coach, Help us, pause?).
* **`invitee_silence`** or **`initiator_silence`**: Multiple consecutive, unanswered messages in history.
* **`positive_behavior`**: Explicit empathy, validation, apology, concession. (Keywords: I understand, That makes sense, I'm sorry, You're right, I appreciate you).

## FINAL CHECK
Is your output a single word? If not, fix it. Your *only* allowed outputs are one of the trigger names above or `silent`.
"""


def build_human_message(
    initiator_name: str,
    invitee_name: str,
    match_subject: str,
    initiator_metadata: list,
    invitee_metadata: list,
    recent_messages: list,
    new_message: dict,
    initiator_id: str,
    invitee_id: str
) -> str:
    """
    Build the human message template for tone analysis.
    
    Args:
        initiator_name: Full name of the initiator
        invitee_name: Full name of the invitee
        match_subject: Subject of the match
        initiator_metadata: List of metadata questions/answers for initiator
        invitee_metadata: List of metadata questions/answers for invitee
        recent_messages: List of recent conversation messages
        new_message: The new message to analyze
        initiator_id: ID of the initiator
        invitee_id: ID of the invitee
    
    Returns:
        Formatted human message string
    """
    # Build initiator perspective
    initiator_perspective = ""
    if initiator_metadata:
        for item in initiator_metadata:
            question_id = item.get("question_id", "")
            choice = item.get("choice", "")
            initiator_perspective += f"{question_id} : {choice}\n"
    
    # Build invitee perspective
    invitee_perspective = ""
    if invitee_metadata:
        for item in invitee_metadata:
            question_id = item.get("question_id", "")
            choice = item.get("choice", "")
            invitee_perspective += f"{question_id} : {choice}\n"
    
    # Build recent conversation history
    conversation_history = ""
    if recent_messages:
        for msg in recent_messages:
            sender_id = msg.get("sender_id")
            body = msg.get("body", "")
            if sender_id == initiator_id:
                conversation_history += f"{initiator_name} (Initiator): {body}\n"
            elif sender_id == invitee_id:
                conversation_history += f"{invitee_name} (Invitee): {body}\n"
    
    # Build last message
    new_message_sender_id = new_message.get("sender_id")
    new_message_body = new_message.get("body", "")
    if new_message_sender_id == initiator_id:
        last_message = f"{initiator_name} (Initiator): {new_message_body}"
    elif new_message_sender_id == invitee_id:
        last_message = f"{invitee_name} (Invitee): {new_message_body}"
    else:
        last_message = f"Unknown: {new_message_body}"
    
    # Build the full message
    message = f"""{initiator_name} is Initiator of the spar and {invitee_name} is Invitee.

The subject of match is **{match_subject}**

This is the Initiator's Perspect for this spar.
{initiator_perspective}

This is the Invitee's Perspect for this spar.
{invitee_perspective}

Recent Conversation History:
{conversation_history}

Last Message: 
{last_message}"""
    
    return message

