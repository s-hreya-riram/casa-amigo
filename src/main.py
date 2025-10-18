from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from uuid import UUID
from typing import Optional

# Import services
from services import AuthService, UserService, TenantProfileService, ReminderService, ConversationService, PropertyService, TenancyService
from services.schema import (
    UsersInsert, UsersUpdate,
    TenantProfilesInsert, TenantProfilesUpdate,
    RemindersInsert,
    MessagesInsert, ConversationsInsert,
    PropertyPreferencesInsert, PropertyPreferencesUpdate,
    TenancyAgreementsInsert
)

# Import exceptions
from core.exceptions import (
    NotFoundError, ValidationError, AuthenticationError, OperationError
)

# Initialize FastAPI app
app = FastAPI(
    title="FAST APIs for Casa Amigo",
    description="Backend API for Casa Amigo rental assistant",
    version="1.0.0"
)

# Initialize services
auth_service = AuthService()
user_service = UserService()
tenant_profile_service = TenantProfileService()
reminder_service = ReminderService()
conversation_service = ConversationService()
property_service = PropertyService()
tenancy_service = TenancyService()

# Security
security = HTTPBearer(auto_error=False)

# ==================== HELPER FUNCTIONS ====================

def _handle_service_error(e: Exception, status_code: int = 400):
    """Convert service exceptions to HTTP exceptions"""
    if isinstance(e, NotFoundError):
        raise HTTPException(status_code=404, detail=str(e))
    elif isinstance(e, AuthenticationError):
        raise HTTPException(status_code=401, detail=str(e))
    elif isinstance(e, ValidationError):
        raise HTTPException(status_code=422, detail=str(e))
    elif isinstance(e, OperationError):
        raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=status_code, detail=str(e))

# ==================== AUTH ROUTES ====================
@app.post("/auth/signup", tags=["Auth"])
async def signup(email: str, name: str, password: str, user_type: str = "tenant"):
    """Create a new user account"""
    try:
        user = auth_service.signup(email, name, password, user_type)
        return {"user_id": user.get("user_id"), "email": user.get("email_id"), "name": user.get("name"), "user_type": user.get("user_type")}
    except Exception as e:
        _handle_service_error(e)

@app.post("/auth/login", tags=["Auth"])
async def login(email: str, password: str):
    """Authenticate user and return user info"""
    try:
        user = auth_service.login(email, password)
        return {
            "user_id": user.get("user_id"),
            "email": user.get("email_id"),
            "name": user.get("name"),
            "user_type": user.get("user_type")
        }
    except Exception as e:
        _handle_service_error(e, status_code=401)


# ==================== USER ROUTES ====================

@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: UUID):
    """Get user details by ID"""
    try:
        user = user_service.get_user(user_id)
        return user
    except Exception as e:
        _handle_service_error(e)


@app.post("/users", tags=["Users"])
async def create_user(user: UsersInsert):
    """Create a new user"""
    try:
        created_user = user_service.create_user(user)
        return created_user
    except Exception as e:
        _handle_service_error(e)


@app.put("/users/{user_id}", tags=["Users"])
async def update_user(user_id: UUID, user: UsersUpdate):
    """Update user details"""
    try:
        updated_user = user_service.update_user(user_id, user)
        return updated_user
    except Exception as e:
        _handle_service_error(e)


# ==================== USER PROFILE ROUTES ====================

@app.get("/tenantprofiles/{user_id}", tags=["Tenant Profiles"])
async def get_tenant_profile(user_id: UUID):
    """Get user's tenant profile"""
    try:
        profile = tenant_profile_service.get_profile(user_id)
        return profile
    except Exception as e:
        _handle_service_error(e)


@app.post("/tenantprofiles", tags=["Tenant Profiles"])
async def create_tenant_profile(profile: TenantProfilesInsert):
    """Create a new tenant profile"""
    try:
        created_profile = tenant_profile_service.create_profile(profile)
        return created_profile
    except Exception as e:
        _handle_service_error(e)


@app.put("/tenantprofiles/{profile_id}", tags=["Tenant Profiles"])
async def update_tenant_profile(profile_id: UUID, profile: TenantProfilesUpdate):
    """Update user's tenant profile"""
    try:
        updated_profile = tenant_profile_service.update_profile(profile_id, profile)
        return updated_profile
    except Exception as e:
        _handle_service_error(e)


# ==================== REMINDERS ROUTES ====================

@app.get("/reminders/{user_id}", tags=["Reminders"])
async def list_reminders(user_id: UUID):
    """List all reminders for a user"""
    try:
        reminders = reminder_service.list_reminders(user_id)
        return {"reminders": reminders}
    except Exception as e:
        _handle_service_error(e)


@app.post("/reminders", tags=["Reminders"])
async def create_reminder(reminder: RemindersInsert):
    """Create a new reminder"""
    try:
        created_reminder = reminder_service.create_reminder(reminder)
        return created_reminder
    except Exception as e:
        _handle_service_error(e)


@app.post("/reminders/{reminder_id}/send", tags=["Reminders"])
async def send_reminder(reminder_id: UUID, user_id: UUID):
    """Send/trigger a reminder (for agentic pipeline)"""
    try:
        notification = reminder_service.send_reminder(reminder_id, user_id)
        return {"status": "sent", "notification": notification}
    except Exception as e:
        _handle_service_error(e)


# ==================== CONVERSATIONS ROUTES ====================

@app.get("/conversations/{user_id}", tags=["Conversations"])
async def list_conversations(user_id: UUID):
    """List all conversations for a user"""
    try:
        conversations = conversation_service.list_conversations(user_id)
        return {"conversations": conversations}
    except Exception as e:
        _handle_service_error(e)


@app.post("/conversations/{conversation_id}/messages", tags=["Conversations"])
async def add_message_to_conversation(conversation_id: UUID, message: MessagesInsert):
    """Add a message to conversation history"""
    try:
        added_message = conversation_service.add_message(conversation_id, message)
        return added_message
    except Exception as e:
        _handle_service_error(e)


@app.get("/conversations/{conversation_id}/messages", tags=["Conversations"])
async def get_conversation_messages(conversation_id: UUID, limit: int = 50):
    """Get all messages from a conversation"""
    try:
        messages = conversation_service.get_messages(conversation_id, limit)
        return {"messages": messages}
    except Exception as e:
        _handle_service_error(e)

@app.post("/conversations", tags=["Conversations"])
async def create_conversation(conversation: ConversationsInsert):
    """Create a new conversation"""
    try:
        created_conversation = conversation_service.create_conversation(conversation)
        return created_conversation
    except Exception as e:
        _handle_service_error(e)

# ==================== PROPERTY PREFERENCES ROUTES ====================

@app.get("/preferences/{user_id}", tags=["Property Preferences"])
async def get_property_preferences(user_id: UUID):
    """Get user's property preferences"""
    try:
        preferences = property_service.get_preferences(user_id)
        return preferences
    except Exception as e:
        _handle_service_error(e)


@app.post("/preferences", tags=["Property Preferences"])
async def create_property_preferences(preferences: PropertyPreferencesInsert):
    """Create user's property preferences"""
    try:
        created_preferences = property_service.create_preferences(preferences)
        return created_preferences
    except Exception as e:
        _handle_service_error(e)


@app.put("/preferences/{preference_id}", tags=["Property Preferences"])
async def update_property_preferences(preference_id: UUID, preferences: PropertyPreferencesUpdate):
    """Update user's property preferences"""
    try:
        updated_preferences = property_service.update_preferences(preference_id, preferences)
        return updated_preferences
    except Exception as e:
        _handle_service_error(e)


# ==================== PROPERTY ROUTES ====================

@app.get("/properties", tags=["Properties"])
async def get_properties(limit: int = 20, offset: int = 0):
    """Get properties with pagination"""
    try:
        properties = property_service.get_properties(limit, offset)
        return {"properties": properties, "count": len(properties)}
    except Exception as e:
        _handle_service_error(e)


@app.post("/properties/search", tags=["Properties"])
async def search_properties_by_preferences(user_id: UUID):
    """Search properties matching user's preferences"""
    try:
        matching_properties = property_service.search_by_preferences(user_id)
        return {"properties": matching_properties, "count": len(matching_properties)}
    except Exception as e:
        _handle_service_error(e)

@app.post("/properties", tags=["Properties"])
async def create_property(property_data: dict):
    """Create a new property"""
    try:
        property_obj = property_service.create_property(property_data)
        return property_obj
    except Exception as e:
        _handle_service_error(e)


# ==================== TENANCY AGREEMENT ROUTES ====================

@app.get("/tenancy-agreements/{agreement_id}", tags=["Tenancy Agreements"])
async def get_tenancy_agreement(agreement_id: UUID):
    """Get a specific tenancy agreement"""
    try:
        agreement = tenancy_service.get_agreement(agreement_id)
        return agreement
    except Exception as e:
        _handle_service_error(e)


@app.post("/tenancy-agreements", tags=["Tenancy Agreements"])
async def create_tenancy_agreement(agreement: TenancyAgreementsInsert):
    """Create a new tenancy agreement"""
    try:
        created_agreement = tenancy_service.create_agreement(agreement)
        return created_agreement
    except Exception as e:
        _handle_service_error(e)


# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)