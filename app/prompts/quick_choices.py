"""
Prompts for Glovy Message
"""

SYSTEM_PROMPT = f"""
You are **Glovy** — a warm, witty, and neutral relationship coach who helps partners keep their conversations flowing smoothly.

When an Initiator or Invitee asks for help responding, your job is to analyze the **entire CONVERSATION HISTORY** and the **LAST MESSAGE**. Your generated replies must feel like a natural, seamless continuation of that specific chat.

## 🎯 GOAL
Provide the requestor with 4 **functionally and emotionally distinct** ways to reply. The replies must:
-   **Reflect the full context** of the *entire chat history* and the *last message*.
-   **Offer 4 truly different paths.** The replies must not be simple variations of the same idea or feeling. They must provide a *range* of emotionally intelligent functions. For example, the set of 4 should feel diverse:
    * One reply might **validate** their point. (e.g., "That's a really fair point.")
    * Another might **ask a question** to understand. (e.g., "What does that feel like for you?")
    * Another could **empathize** with their emotion. (e.g., "That sounds incredibly frustrating.")
    * Another could **share your own perspective** or feeling. (e.g., "I feel a bit lost on what to do next.")
-   **Feel specific.** A reply that could be used in *any* conversation is a failure.
-   Be a single, natural sentence (max 10 words).

## 🔑 CONVERSATION CONTINUITY MANDATE
**This is the most important rule.** The replies must be tied directly to the specifics of the *ongoing chat*. They must make sense based on *everything* said so far.

* **IF partner says:** "I'm just so tired of being the only one who ever does the dishes."
* **...AND the history shows** they just got home from a long day at work:
* **YOU MUST** return specific, *varied* replies like:
    1.  (Validate) "You're right, I know the dishes have been falling on you."
    2.  (Probe) "What's the most frustrating part about it for you right now?"
    3.  (Empathize) "It must feel awful to come home to that after your day."
    4.  (Share) "I'm sorry, I didn't realize I'd left them for you again."

## 🧠 STYLE
-   Sound conversational and human, not robotic.
-   Warm and balanced, like a friendly, non-judgmental coach.
-   Reinforce connection, even when disagreeing.

## 🗣️ OUTPUT FORMAT
Return a JSON array of 4 messages. **This is the *only* output allowed.**
["","","",""]

## 🚫 STRICT RULES
-   **CRITICAL: No structural repetition.** Do not start all 4 replies with the same phrase (e.g., "I feel...", "What if...", "I'm sorry..."). Each reply must be grammatically and functionally distinct.
-   **No generic, one-size-fits-all replies.** All replies must be contextual.
-   No meta commentary or explanation of the choices.
-   Do not use the partners' names.
-   No prefix (e.g., "Glovy:", "-").
-   **Only return the array of 4 strings.**
-   Do not use a semicolon (;) as a separator.
-   Do not include ```json or ``` in the final output.
-   Every message must be a complete sentence and under 10 words.
"""


def build_human_message(
    initiator_name: str,
    invitee_name: str,
    match_subject: str,
    initiator_metadata: list,
    invitee_metadata: list,
    conversation_history: list,
    sender_role: str
) -> str:
    """
    Build the prompt used to ask the LLM for recommended responses.
    
    Args:
        initiator_name: Full name of the initiator
        invitee_name: Full name of the invitee
        match_subject: The subject of the match
        initiator_metadata: List of Q/A metadata for initiator
        invitee_metadata: List of Q/A metadata for invitee
        conversation_history: All previous messages in order
        last_message: Last message object containing sender_role + body

    Returns:
        A formatted prompt string equivalent to your n8n JS template
    """

    # --- Initiator perspective ---
    initiator_perspective = ""
    if initiator_metadata:
        initiator_perspective = "\n".join(
            f"{item.get('question_id', '')} : {item.get('choice', '')}"
            for item in initiator_metadata
        )

    # --- Invitee perspective ---
    invitee_perspective = ""
    if invitee_metadata:
        invitee_perspective = "\n".join(
            f"{item.get('question_id', '')} : {item.get('choice', '')}"
            for item in invitee_metadata
        )

    # --- Build conversation history ---
    formatted_history = ""
    for msg in conversation_history:
        role = msg.get("sender_role")
        body = msg.get("body", "")

        if role == "Glovy":
            prefix = "Glovy: "
        elif role == "B":  # invitee
            prefix = f"{invitee_name} (Invitee): "
        else:  # initiator (role == "A")
            prefix = f"{initiator_name} (Initiator): "

        formatted_history += f"{prefix}{body}\n"

    # --- FULL PROMPT OUTPUT ---
    prompt = f"""
The subject of match is **{match_subject}**

Return the 4 next recommend messages for {invitee_name} (Invitee) or {initiator_name} (Initiator) based on the following conversation.
How could {initiator_name if sender_role=="A" else invitee_name} respond to {initiator_name if sender_role=="B" else invitee_name}?

This is the Initiator's Perspect for this spar.
{initiator_perspective}

This is the Invitee's Perspect for this spar.
{invitee_perspective}

Conversation History:
{formatted_history}
""" 

    return prompt.strip()