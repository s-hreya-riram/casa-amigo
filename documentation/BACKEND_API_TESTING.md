# Backend API Testing Guide

## Quick Start

### 1. Start the Backend
```bash
cd src
python -m uvicorn main:app --reload
```

Leave this running in the terminal and if you choose to run testing perform the testing using the curl commands in a different tab of the terminal.

### 2. Access Interactive API Docs
Visit `http://localhost:8000/docs` in your browser. This Swagger UI lets you test every endpoint without writing curl commands. You can use the attributes from the curl commands 

---

### 3. Testing with Curl

#### Complete User Journey Test

**Step 1: Signup**
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "name": "Test User",
    "password": "testpassword123",
    "user_type": "tenant"
  }'
```

Save the `user_id` from response.

---

**Step 2: Login**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "testpassword123"
  }'
```

Verify you get the same user data back.

---

**Step 3: Create Tenant Profile**
```bash
curl -X POST http://localhost:8000/tenantprofiles \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID_FROM_STEP_1",
    "has_pets": false,
    "household_size": 1,
    "monthly_income": 5000,
    "nationality": "Singapore",
    "preferred_move_in_date": "2025-12-01T00:00:00Z",
    "visa_status": "PR",
    "is_smoker": false
  }'
```

---

**Step 4: Create Property Preferences**
```bash
curl -X POST http://localhost:8000/preferences \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID_FROM_STEP_1",
    "min_budget": 2000,
    "max_budget": 4000,
    "min_bedrooms": 1,
    "max_bedrooms": 2,
    "min_bathrooms": 1,
    "max_sqft": 1000,
    "property_type": ["apartment", "condo"],
    "preferred_neighborhoods": ["Orchard", "Tiong Bahru"],
    "required_amenities": ["parking"]
  }'
```

---

**Step 5: View All Properties**
```bash
curl -X GET "http://localhost:8000/properties?limit=10&offset=0"
```

---

**Step 6: Search Properties by Preferences**
```bash
curl -X POST "http://localhost:8000/properties/search?user_id=YOUR_USER_ID_FROM_STEP_1"
```

Should return properties matching your preferences.

---

**Step 7: Create a Conversation**
```bash
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID_FROM_STEP_1"
  }'
```

Save the `conversation_id`.

---

**Step 8: Add Messages to Conversation**
```bash
curl -X POST "http://localhost:8000/conversations/YOUR_CONVERSATION_ID_FROM_STEP_7/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Looking for 2 bedroom apartment",
    "role": "user"
  }'
```

Add another message as assistant:
```bash
curl -X POST "http://localhost:8000/conversations/YOUR_CONVERSATION_ID_FROM_STEP_7/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I found 3 properties matching your criteria",
    "role": "assistant"
  }'
```

---

**Step 9: Retrieve Conversation Messages**
```bash
curl -X GET "http://localhost:8000/conversations/YOUR_CONVERSATION_ID_FROM_STEP_7/messages?limit=50"
```

---

**Step 10: Create a Reminder**
```bash
curl -X POST http://localhost:8000/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID_FROM_STEP_1",
    "reminder_type_id": 1,
    "description": "Sign letter of intent",
    "status": "active"
  }'
```

Save the `reminder_id`.

---

**Step 11: List Reminders**
```bash
curl -X GET "http://localhost:8000/reminders/YOUR_USER_ID_FROM_STEP_1"
```

---

**Step 12: Send a Reminder**
```bash
curl -X POST "http://localhost:8000/reminders/YOUR_REMINDER_ID_FROM_STEP_10/send?user_id=YOUR_USER_ID_FROM_STEP_1"
```

---

**Step 13: Create Tenancy Agreement**
```bash
curl -X POST http://localhost:8000/tenancy-agreements \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "YOUR_USER_ID_FROM_STEP_1",
    "property_id": "PROPERTY_ID_FROM_STEP_5",
    "property_agent_id": "YOUR_USER_ID_FROM_STEP_1",
    "start_date": "2025-12-01T00:00:00Z",
    "end_date": "2026-12-01T00:00:00Z",
    "monthly_rent": 3500,
    "is_signed_by_all_parties": false
  }'
```

Save the `id`.

---

**Step 14: Retrieve Tenancy Agreement**
```bash
curl -X GET "http://localhost:8000/tenancy-agreements/YOUR_TENANCY_AGREEMENT_ID_FROM_STEP_13"
```

---

## Testing Individual Endpoints

### Test User Update
```bash
curl -X PUT "http://localhost:8000/users/YOUR_USER_ID_FROM_STEP_1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name"
  }'
```

### Test Get User
```bash
curl -X GET "http://localhost:8000/users/YOUR_USER_ID_FROM_STEP_1"
```

### Test Get Tenant Profile
```bash
curl -X GET "http://localhost:8000/tenantprofiles/YOUR_USER_ID_FROM_STEP_1"
```

### Test Update Tenant Profile
```bash
curl -X PUT "http://localhost:8000/tenantprofiles/YOUR_PROFILE_ID_FROM_STEP_3" \
  -H "Content-Type: application/json" \
  -d '{
    "monthly_income": 6000
  }'
```

### Test Get Preferences
```bash
curl -X GET "http://localhost:8000/preferences/YOUR_USER_ID_FROM_STEP_1"
```

### Test Update Preferences
```bash
curl -X PUT "http://localhost:8000/preferences/YOUR_PREFERENCE_ID_FROM_STEP_4" \
  -H "Content-Type: application/json" \
  -d '{
    "max_budget": 5000
  }'
```

### Test List Conversations
```bash
curl -X GET "http://localhost:8000/conversations/YOUR_USER_ID_FROM_STEP_1"
```
---

## Common Testing Issues

All 4xx errors are user input issue, all 5xx are server side issues.

For 400 Bad Request, check JSON formatting and field names
For 404 Not Found, check that the relevant UUID is correct and the applicable resource(s) exists
For 422 Validation error, check required fields are provided and data types match
For 500 Server Error, we need to add logs so in the meantime some manual debugging may be needed for errors that aren't obvious.

---