from typing import Optional, Literal
from pydantic import BaseModel, Field, UUID4
import requests
from utils.current_auth import get_current_auth
from utils.utils import to_utc_iso
import os
import streamlit as st
from uuid import UUID, uuid4
from openai import OpenAI

class ReminderPayload(BaseModel):
    user_id: UUID
    reminder_type_id: int
    description: str
    status: str
    reminder_date: str | None = None
    reminder_id: UUID
    recurring_rule: str | None = None

class ReminderInput(BaseModel):
    action: Optional[Literal["create", "list", "send", "cancel"]] = Field(
        "create", description="Action to perform on reminders."
    )
    reminder_type_id: Optional[int] = Field(
        None, description="1=LOI, 2=Deposit, 3=Lease, 4=Rent, 5=Renewal, 6=Move out."
    )
    description: Optional[str] = Field(None, description="Human-readable label.")
    reminder_date: Optional[str] = Field(
        None,
        description="Date/time of reminder (ISO8601, e.g. '2025-11-02T12:00:00')."
    )
    recurring_rule: Optional[str] = Field(
        None,
        description="Recurring rule e.g. 'monthly:1@09:00' for rent."
    )
    reminder_id: Optional[str] = Field(None, description="Used for cancel/send.")
    user_id: Optional[str] = Field(
        "demo_user", description="Hardcoded until auth is added."
    )

def _get_api_base() -> str:
    try:
        if "api" in st.secrets and "base_url" in st.secrets["api"]:
            return st.secrets["api"]["base_url"].rstrip("/")
    except Exception:
        pass
    return os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")

def _auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

def _generate_email_friendly_description(task_label: str, reminder_type_id: int, llm_client) -> str:
    """
    Use OpenAI to generate a friendly, professional email-ready description.
    Returns a structured description that Lambda can use directly.
    
    Args:
        task_label: The task description
        reminder_type_id: Type of reminder (1-6)
        llm_client: OpenAI client instance from the agent
    """
    type_context = {
        1: "signing a Letter of Intent for a rental property",
        2: "paying the security deposit for a rental property",
        3: "signing the lease agreement for a rental property",
        4: "paying monthly rent",
        5: "reviewing lease renewal options or giving notice",
        6: "moving out and returning keys"
    }
    
    context = type_context.get(reminder_type_id, "completing a rental task")
    
    try:
        client = llm_client
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that creates friendly, professional email reminders for rental tasks. "
                        "Generate a clear, warm reminder message that includes:\n"
                        "1. A friendly subject line (max 60 chars)\n"
                        "2. A brief, encouraging body message (2-3 sentences)\n"
                        "Format as JSON: {\"subject\": \"...\", \"body\": \"...\"}"
                    )
                },
                {
                    "role": "user",
                    "content": f"Create a reminder for: {task_label}. Context: {context}"
                }
            ],
            temperature=0.7,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        # Return structured format that Lambda can parse
        return json.dumps({
            "subject": result.get("subject", f"Reminder: {task_label}"),
            "body": result.get("body", f"This is a friendly reminder to {task_label}."),
            "task": task_label,
            "type": context
        })
        
    except Exception as e:
        print(f"[REMINDER] Failed to generate email content: {e}")
        # Fallback to simple format
        return json.dumps({
            "subject": f"Reminder: {task_label}",
            "body": f"This is a friendly reminder to {task_label}.",
            "task": task_label,
            "type": context
        })

def notification_workflow_tool(
    input: ReminderInput | dict | None = None,
    **kwargs,
) -> str:
    """
    Create / list / send (and stub cancel) reminders by
    talking to the running FastAPI backend.
    
    Args:
        input: Reminder input data
        **kwargs: Additional arguments including auth and llm_client
    """
    print(f"[REMINDER] RAW INPUT: input={input}, type={type(input)}")
    print(f"[REMINDER] KWARGS: {kwargs}")
    
    API_BASE = _get_api_base()

    # Normalize input
    if isinstance(input, ReminderInput):
        data = input.dict(exclude_none=True)
    elif isinstance(input, dict):
        data = dict(input)
    else:
        data = {}
    data.update(kwargs or {})
    
    # Extract llm_client from kwargs (don't add to data dict)
    llm_client = kwargs.get('llm_client')
    
    print(f"[REMINDER] NORMALIZED DATA: {data}")
    print(f"[REMINDER] Has LLM client: {llm_client is not None}")

    # Get auth from injected kwargs
    auth = data.get('_injected_auth') or kwargs.get('_injected_auth', {})
    
    user_id = auth.get("user_id")
    token = auth.get("token")
    print(f"[REMINDER] Auth received: user_id={user_id}, has_token={bool(token)}")

    if not user_id or not token:
        print(f"[REMINDER] AUTH MISSING! User_ID: {user_id}, Token: {token}")
        return "Please log in first before attempting to list reminders."

    # ✅ Extract action (with default)
    action = (data.get("action") or "list").lower() # Default to "list" if not specified
    print(f"[REMINDER] ACTION: {action}")
    reminder_type_id = data.get("reminder_type_id")
    description = data.get("description")
    reminder_date = data.get("reminder_date")
    recurring_rule = data.get("recurring_rule")
    reminder_id = data.get("reminder_id")

    # Display labels for nicer UX
    type_labels = {
        1: "Sign letter of intent",
        2: "Pay security deposit",
        3: "Sign lease",
        4: "Pay rent",
        5: "Review renewal / give notice",
        6: "Move out / return keys",
    }
    task_label = description or type_labels.get(reminder_type_id) or "this task"

    # ------------------------------------------------------------------
    # LIST reminders
    # ------------------------------------------------------------------
    if action == "list":
        try:
            print(f"[REMINDER] Listing reminders for user: {user_id}")
            resp = requests.get(
                f"{API_BASE}/reminders/{user_id}",
                headers=_auth_headers(token),
                timeout=5,
            )
            print(f"[REMINDER] Response status: {resp.status_code}")
            print(f"[REMINDER] Response body: {resp.text[:500]}")
            if resp.status_code != 200:
                return "Are you logged in? I couldn't load your reminders from the server."

            body = resp.json()
            reminders = body.get("reminders", [])
            if not reminders:
                return "You don't have any active reminders right now."

            lines = ["Here are your active reminders:"]
            for r in reminders:
                rid = r.get("reminder_id") or r.get("id") or "?"
                what = r.get("description") or "Reminder"
                status = r.get("status") or "active"
                # time can be one-off (reminder_date) or recurring (recurrence_pattern)
                when = (
                    r.get("reminder_date")
                    or r.get("recurrence_pattern")
                    or "(no time set)"
                )
                lines.append(f"• {what} — {when} [{status}] (id: {rid})")

            return "\n".join(lines)

        except Exception as e:
            print(f"[REMINDER] EXCEPTION in list: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry — are you logged in? I hit an error while fetching your reminders."

    # ------------------------------------------------------------------
    # SEND reminder now
    # ------------------------------------------------------------------
    if action == "send":
        if not reminder_id:
            return "Which reminder should I send right now? Please give me the id."

        try:
            resp = requests.post(
                f"{API_BASE}/reminders/{reminder_id}/send",
                params={"user_id": user_id},
                headers=_auth_headers(token),
                timeout=5,
            )
            if resp.status_code != 200:
                return f"I couldn't send reminder {reminder_id} (server error)."
            return f"Okay — I've sent reminder {reminder_id} now."
        except Exception as e:
            return f"Sorry — I tried to send reminder {reminder_id} but hit a network error."

    # ------------------------------------------------------------------
    # CANCEL
    # ------------------------------------------------------------------
    if action == "cancel":
        if not reminder_id:
            return "Which reminder should I cancel? Please give me the id."
        return f"Done — I'll cancel reminder {reminder_id} once the server supports it."

    # ------------------------------------------------------------------
    # CREATE reminder
    # ------------------------------------------------------------------

    # For rent reminders (recurring):
    if reminder_type_id == 4:
        if not recurring_rule:
            return (
                "Sure. Which day of the month and what time should I remind you to pay rent? "
                "For example: '1st at 9am'."
            )

        try:
            # Generate email-friendly description using injected LLM client
            email_description = _generate_email_friendly_description(
                task_label, reminder_type_id, llm_client
            ) if llm_client else task_label
            
            payload_obj = ReminderPayload(
                user_id=user_id,
                reminder_type_id=4,
                description=email_description,
                status="active",
                recurring_rule=recurring_rule,
                reminder_id=uuid4()
            )
            
            payload = payload_obj.model_dump(mode='json', exclude_none=True)
            
            resp = requests.post(
                f"{API_BASE}/reminders",
                headers=_auth_headers(token),
                json=payload,
                timeout=5,
            )
            if resp.status_code not in (200, 201):
                return "I couldn't save that rent reminder to the server."

            created = resp.json()
            rid = created.get("id") or created.get("reminder_id") or "(no id)"
            return (
                f"Okay — I'll remind you to {task_label} every month "
                f"({recurring_rule}). I've saved it as reminder {rid}."
            )
        except Exception as e:
            print(f"[REMINDER] EXCEPTION in rent reminder: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return (
                "I tried to save that rent reminder, but I hit a network error. "
                "I'll still remember it for this chat, but it may not show up in your list yet."
            )

    # For non-rent reminders:
    if not reminder_date:
        return (
            f"Sure. When should I remind you to {task_label}? "
            "You can give a specific date/time like '2025-11-02 at 6pm'."
        )

    reminder_date = to_utc_iso(reminder_date)
    print(f"[REMINDER] Converted reminder_date to UTC ISO: {reminder_date}")

    try:
        # Generate email-friendly description using injected LLM client
        email_description = _generate_email_friendly_description(
            task_label, reminder_type_id, llm_client
        ) if llm_client else task_label
        
        payload_obj = ReminderPayload(
            user_id=user_id,
            reminder_type_id=reminder_type_id,
            description=email_description,
            status="active",
            reminder_date=reminder_date,
            reminder_id=uuid4()
        )
        
        payload = payload_obj.model_dump(mode='json')
        print("Creating reminder with payload:", payload)

        resp = requests.post(
            f"{API_BASE}/reminders",
            headers=_auth_headers(token),
            json=payload,
            timeout=5,
        )
        print(f"[REMINDER] Create response status: {resp.status_code}")
        print(f"[REMINDER] Create response body: {resp.text[:500]}")
        if resp.status_code not in (200, 201):
            return "I couldn't save that reminder to the server."

        created = resp.json()
        print(f"[REMINDER] Create response body: {created}")
        rid = created.get("reminder_id") or created.get("id") or "(no id)"

        return f"Perfect! I've set a reminder to {task_label.lower()}. You'll get an email when it's time."

    except Exception as e:
        print(f"[REMINDER] EXCEPTION in create: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return (
            "I tried to save that reminder but hit a network error. "
            "I'll still remember it for this chat, but it may not show up in your list yet."
        )