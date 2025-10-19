# Documentation and testing for backend APIs

You can run the 
```bash
cd src
python -m uvicorn main:app --reload
```

Interactive docs at `http://localhost:8000/docs` - you can either test individual APIs here or 

## Authentication Endpoints

### POST /auth/signup
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securepassword123",
  "user_type": "tenant"
}
```

**Parameters:**
- `email` (string, required) — User email address
- `name` (string, required) — User's full name
- `password` (string, required) — Password (minimum 8 characters)
- `user_type` (string, optional) — "tenant" or "property_agent" (defaults to "tenant")

**Response (200):**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "email": "user@example.com",
  "name": "John Doe",
  "user_type": "tenant"
}
```

**Errors:**
- `422` — Validation error (invalid email, short password, etc.)
- `400` — User with email already exists

---

### POST /auth/login
Authenticate a user and receive their profile information.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Parameters:**
- `email` (string, required) — User email
- `password` (string, required) — User password

**Response (200):**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "email": "user@example.com",
  "name": "John Doe",
  "user_type": "tenant"
}
```

**Errors:**
- `401` — Invalid email or password

---

## User Endpoints

### GET /users/{user_id}
Retrieve a specific user's information.

**Parameters:**
- `user_id` (string, path, required) — UUID of the user

**Response (200):**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2025-10-18 10:00:00.000000",
  "user_type": "tenant"
}
```

**Errors:**
- `404` — User not found

---

### POST /users
Create a new user (admin operation).

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "user_type": "property_agent"
}
```

**Response (200):**
```json
{
  "user_id": "uuid",
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "user_type": "property_agent"
}
```

---

### PUT /users/{user_id}
Update user information.

**Parameters:**
- `user_id` (string, path, required) — UUID of the user

**Request Body:**
```json
{
  "name": "John Updated",
  "user_type": "property_agent"
}
```

**Response (200):**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "email": "user@example.com",
  "name": "John Updated",
  "user_type": "property_agent"
}
```

---

## Tenant Profile Endpoints

### GET /tenantprofiles/{user_id}
Get a tenant's profile information.

**Parameters:**
- `user_id` (string, path, required) — UUID of the user

**Response (200):**
```json
{
  "profile_id": "uuid",
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "has_pets": true,
  "household_size": 2,
  "monthly_income": 6000,
  "nationality": "Singapore",
  "preferred_move_in_date": "2025-12-01 00:00:00.000000",
  "visa_status": "PR",
  "is_smoker": false,
  "employment_status": "employed",
  "occupation": "Engineer",
  "created_at": "2025-10-18 10:00:00.000000"
}
```

**Errors:**
- `404` — Profile not found

---

### POST /tenantprofiles
Create a new tenant profile.

**Request Body:**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "has_pets": true,
  "pet_description": "Golden retriever",
  "household_size": 2,
  "monthly_income": 6000,
  "nationality": "Singapore",
  "preferred_move_in_date": "2025-12-01T00:00:00Z",
  "visa_status": "PR",
  "is_smoker": false,
  "employment_status": "employed",
  "occupation": "Software Engineer"
}
```

**Response (200):**
```json
{
  "profile_id": "uuid",
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "has_pets": true,
  ...
}
```

---

### PUT /tenantprofiles/{profile_id}
Update a tenant profile.

**Parameters:**
- `profile_id` (string, path, required) — UUID of the profile

**Request Body:** (all fields optional)
```json
{
  "monthly_income": 7000,
  "occupation": "Senior Engineer"
}
```

**Response (200):** Updated profile object

---

## Property Endpoints

### GET /properties
Get all properties with pagination.

**Query Parameters:**
- `limit` (integer, optional) — Number of results (default: 20)
- `offset` (integer, optional) — Starting index (default: 0)

**Response (200):**
```json
{
  "properties": [
    {
      "property_id": "uuid",
      "address": "123 Orchard Road, Singapore",
      "num_bedrooms": 2,
      "num_bathrooms": 1.5,
      "rent": 3500,
      "sqft": 850,
      "furnished": true,
      "property_type": "apartment",
      "neighborhood": "Orchard",
      "is_pet_friendly": true,
      "amenities": ["gym", "pool", "security"],
      "listing_status": "available",
      "created_at": "2025-10-18 10:00:00.000000"
    }
  ],
  "count": 1
}
```

---

### POST /properties
Create a new property (admin/property agent operation).

**Request Body:**
```json
{
  "address": "456 East Coast Road, Singapore",
  "num_bedrooms": 3,
  "num_bathrooms": 2,
  "rent": 4500,
  "sqft": 1200,
  "furnished": false,
  "property_type": "condo",
  "neighborhood": "East Coast",
  "is_pet_friendly": false,
  "amenities": ["gym", "lounge", "parking"],
  "listing_status": "available"
}
```

**Response (200):** Created property object with `property_id`

---

### POST /properties/search
Search properties matching user's preferences.

**Query Parameters:**
- `user_id` (string, required) — UUID of the user

**Response (200):**
```json
{
  "properties": [
    {
      "property_id": "uuid",
      "address": "123 Orchard Road, Singapore",
      "num_bedrooms": 2,
      "rent": 3500,
      ...
    },
  ],
  "count": 1
}
```

**Errors:**
- `404` — User preferences not found

---

## Property Preferences Endpoints

### GET /preferences/{user_id}
Get user's property search preferences.

**Parameters:**
- `user_id` (string, path, required) — UUID of the user

**Response (200):**
```json
{
  "preference_id": "uuid",
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "min_budget": 2000,
  "max_budget": 4000,
  "min_bedrooms": 1,
  "max_bedrooms": 2,
  "min_bathrooms": 1,
  "max_sqft": 1000,
  "property_type": ["apartment", "condo"],
  "preferred_neighborhoods": ["Orchard", "Tiong Bahru"],
  "required_amenities": ["parking", "gym"],
  "created_at": "2025-10-18T10:00:00+08:00"
}
```

**Errors:**
- `404` — Preferences not found

---

### POST /preferences
Create property preferences for a user.

**Request Body:**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "min_budget": 2000,
  "max_budget": 4000,
  "min_bedrooms": 1,
  "max_bedrooms": 2,
  "min_bathrooms": 1,
  "max_sqft": 1000,
  "property_type": ["apartment", "condo"],
  "preferred_neighborhoods": ["Orchard", "Tiong Bahru"],
  "required_amenities": ["parking", "gym"],
  "max_distance_from_mrt": 500
}
```

**Response (200):** Created preferences object with `preference_id`

---

### PUT /preferences/{preference_id}
Update user's property preferences.

**Parameters:**
- `preference_id` (string, path, required) — UUID of the preferences

**Request Body:** (all fields optional)
```json
{
  "max_budget": 5000,
  "min_bedrooms": 2
}
```

**Response (200):** Updated preferences object

---

## Conversation Endpoints

### GET /conversations/{user_id}
List all conversations for a user.

**Parameters:**
- `user_id` (string, path, required) — UUID of the user

**Response (200):**
```json
{
  "conversations": [
    {
      "conversation_id": "uuid",
      "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
      "created_at": "2025-10-18 10:00:00.000000",
      "updated_at": "2025-10-18 11:00:00.000000"
    }
  ]
}
```

---

### POST /conversations
Create a new conversation.

**Request Body:**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318"
}
```

**Response (200):**
```json
{
  "conversation_id": "uuid",
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "created_at": "2025-10-18 10:00:00.000000"
}
```

---

### POST /conversations/{conversation_id}/messages
Add a message to a conversation.

**Parameters:**
- `conversation_id` (string, path, required) — UUID of the conversation

**Request Body:**
```json
{
  "message": "I'm looking for a 2 bedroom apartment in Orchard",
  "role": "user"
}
```

**Response (200):**
```json
{
  "message_id": "uuid",
  "conversation_id": "uuid",
  "message": "I'm looking for a 2 bedroom apartment in Orchard",
  "role": "user",
  "created_at": "2025-10-18 10:30:00.625732"
}
```

---

### GET /conversations/{conversation_id}/messages
Retrieve all messages from a conversation.

**Parameters:**
- `conversation_id` (string, path, required) — UUID of the conversation
- `limit` (integer, optional) — Max messages to return (default: 50)

**Response (200):**
```json
{
  "messages": [
    {
      "message_id": "uuid",
      "conversation_id": "uuid",
      "message": "I'm looking for a 2 bedroom apartment in Orchard",
      "role": "tenant",
      "created_at": "2025-10-18 10:30:00.625732"
    },
    {
      "message_id": "uuid",
      "conversation_id": "uuid",
      "message": "I found 3 properties matching your criteria",
      "role": "assistant",
      "created_at": "2025-10-18 10:31:00.625732"
    }
  ]
}
```

---

## Reminder Endpoints

### GET /reminders/{user_id}
List all reminders for a user.

**Parameters:**
- `user_id` (string, path, required) — UUID of the user

**Response (200):**
```json
{
  "reminders": [
    {
      "reminder_id": "uuid",
      "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
      "reminder_type_id": 1,
      "description": "Sign letter of intent",
      "status": "active",
      "created_at": "2025-10-18 10:00:00.000000"
    }
  ]
}
```

---

### POST /reminders
Create a new reminder.

**Request Body:**
```json
{
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "reminder_type_id": 1,
  "description": "Sign letter of intent for Orchard property",
  "reminder_date": "2025-11-01 10:00:00.000000",
  "status": "active"
}
```

**Reminder Types:**
- `1` — Sign letter of intent
- `2` — Pay security deposit
- `3` — Sign lease
- `4` — Pay rent (recurring)
- `5` — Review renewal notice
- `6` — Move out

**Response (200):**
```json
{
  "reminder_id": "uuid",
  "user_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "reminder_type_id": 1,
  "description": "Sign letter of intent for Orchard property",
  "status": "active"
}
```

---

### POST /reminders/{reminder_id}/send
Send/trigger a reminder notification.

**Parameters:**
- `reminder_id` (string, path, required) — UUID of the reminder
- `user_id` (string, query, required) — UUID of the user

**Response (200):**
```json
{
  "status": "sent",
  "notification": {
    "notification_id": "uuid",
    "reminder_id": "uuid",
    "user_id": "uuid",
    "delivery_status": "sent",
    "sent_at": "2025-10-18 10:35:00.625732"
  }
}
```

---

## Tenancy Agreement Endpoints

### GET /tenancy-agreements/{agreement_id}
Retrieve a specific tenancy agreement.

**Parameters:**
- `agreement_id` (string, path, required) — UUID of the agreement

**Response (200):**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "property_id": "uuid",
  "property_agent_id": "uuid",
  "start_date": "2025-12-01 00:00:00.000000",
  "end_date": "2026-12-01 00:00:00.000000",
  "monthly_rent": 3500,
  "deposit_amount": 3500,
  "is_signed_by_all_parties": false,
  "status": "pending",
  "created_at": "2025-10-18 10:00:00.000000"
}
```

**Errors:**
- `404` — Agreement not found

---

### POST /tenancy-agreements
Create a new tenancy agreement.

**Request Body:**
```json
{
  "tenant_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "property_id": "fdb7f6b8-ca41-4851-80f8-f66a5c120341",
  "property_agent_id": "660c6b52-4fd6-494d-b2a5-39c4ba773318",
  "start_date": "2025-12-01 00:00:00.000000",
  "end_date": "2026-12-01 00:00:00.000000",
  "monthly_rent": 3500,
  "deposit_amount": 3500,
  "is_signed_by_all_parties": false
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "property_id": "uuid",
  "property_agent_id": "uuid",
  "start_date": "2025-12-01T00:00:00Z",
  "end_date": "2026-12-01T00:00:00Z",
  "monthly_rent": 3500,
  "status": "pending"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- `200` — Success
- `400` — Bad request (invalid data)
- `401` — Unauthorized (invalid credentials)
- `404` — Resource not found
- `422` — Validation error (missing required fields)
- `500` — Server error

---