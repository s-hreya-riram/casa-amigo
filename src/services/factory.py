# src/services_factory.py
from services import (
    AuthService, UserService, TenantProfileService,
    ReminderService, ConversationService, PropertyService, TenancyService
)

auth_service = AuthService()
user_service = UserService()
tenant_profile_service = TenantProfileService()
reminder_service = ReminderService()
conversation_service = ConversationService()
property_service = PropertyService()
tenancy_service = TenancyService()
