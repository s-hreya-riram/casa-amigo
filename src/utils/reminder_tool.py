from typing import Optional, Literal
from pydantic import BaseModel, Field
import requests
from utils.current_auth import get_current_auth

# ----------- TODO: GET THIS FROM STREAMLIT AFTER WE ADD LOGIN PAGE  // for testing purposes use curl and get replace with your auth token and test ------
API_BASE = "http://127.0.0.1:8000"
#DEMO_USER_ID = "2dbe55f1-5332-461c-87f1-4f7dd76dbb8f"
#EMO_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyZGJlNTVmMS01MzMyLTQ2MWMtODdmMS00ZjdkZDc2ZGJiOGYiLCJleHAiOjE3NjE4MTQyODR9.mWrEgJUw3mp-k_uSbtHbV1tMCJlQvg2dUIrQnzwo34U"

#user_id = runtime.get("user_id") or DEMO_USER_ID
#token = runtime.get("token") or DEMO_AUTH_TOKEN

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

import requests

def _auth_headers(token):
    # central place for auth header
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

def notification_workflow_tool(
    input: ReminderInput | dict | None = None,
    **kwargs,
) -> str:
    """
    Create / list / send (and stub cancel) reminders by
    talking to the running FastAPI backend.

    Safe: never raises, always returns a friendly string.
    """

    # ----- normalize input -----
    if isinstance(input, ReminderInput):
        data = input.dict(exclude_none=True)
    elif isinstance(input, dict):
        data = dict(input)
    else:
        data = {}
    data.update(kwargs or {})

    runtime = get_current_auth()
    print("hellooooooo Runtime auth from context:", runtime)
    user_id = runtime.get("user_id") 
    token = runtime.get("token") 

    # pull fields
    action = (data.get("action") or "create").lower()
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
            resp = requests.get(
                f"{API_BASE}/reminders/{user_id}",
                headers=_auth_headers(token),
                timeout=5,
            )
            if resp.status_code != 200:
                return "I couldn't load your reminders from the server."

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
            #debug_log("tool_error", tool="notification_workflow_tool", error=str(e))
            return "Sorry — I hit an error while fetching your reminders."

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
            #debug_log("tool_error", tool="notification_workflow_tool", error=str(e))
            return f"Sorry — I tried to send reminder {reminder_id} but hit a network error."

    # ------------------------------------------------------------------
    # CANCEL (stub, unless you have PATCH /reminders/{id})
    # ------------------------------------------------------------------
    if action == "cancel":
        if not reminder_id:
            return "Which reminder should I cancel? Please give me the id."
        # TODO when backend adds: PATCH /reminders/{id} status='cancelled'
        return f"Done — I'll cancel reminder {reminder_id} once the server supports it."

    # ------------------------------------------------------------------
    # CREATE reminder
    # ------------------------------------------------------------------

    # rent (type 4) → recurring monthly
    if reminder_type_id == 4:
        if not recurring_rule:
            return (
                "Sure. Which day of the month and what time should I remind you to pay rent? "
                "For example: '1st at 9am'."
            )

        payload = {
            "user_id": user_id,
            "reminder_type_id": 4,
            "description": task_label,
            "status": "active",
            "recurring_rule": recurring_rule,
        }

        try:
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
            #debug_log("tool_error", tool="notification_workflow_tool", error=str(e))
            return (
                "I tried to save that rent reminder, but I hit a network error. "
                "I'll still remember it for this chat, but it may not show up in your list yet."
            )

    # non-rent → one-off date/time
    if not reminder_date:
        return (
            f"Sure. When should I remind you to {task_label}? "
            "You can give a specific date/time like '2025-11-02 at 6pm'."
        )

    payload = {
    "user_id": user_id,
    "reminder_type_id": reminder_type_id,
    "description": task_label,
    "status": "active",
    "reminder_date": reminder_date,
}

    try:
        resp = requests.post(
            f"{API_BASE}/reminders",
            headers=_auth_headers(token),
            json=payload,
            timeout=5,
        )
        if resp.status_code not in (200, 201):
            return "I couldn't save that reminder to the server."

        created = resp.json()
        rid = created.get("reminder_id") or created.get("id") or "(no id)"

        return (
            f"Got it — I'll remind you to {task_label} on {reminder_date}. "
            f"I've saved it as reminder {rid}."
        )

    except Exception as e:
        #debug_log("tool_error", tool="notification_workflow_tool", error=str(e))
        return (
            "I tried to save that reminder but hit a network error. "
            "I'll still remember it for this chat, but it may not show up in your list yet."
        )