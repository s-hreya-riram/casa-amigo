# Casa Amigo 🏠

Casa Amigo is an AI-powered rental assistant that helps tenants navigate lease agreements, explore neighborhoods, and manage rental deadlines through intelligent conversation and automated reminders.

## What it does

Casa Amigo uses agentic workflows to provide specialized assistance to intelligently classify user intent and routes to specialized tools :

1. **Lease Q & A**: Uses Singapore rental documents to provide accurate advice for user Q & A
2. **Smart Reminders**: Creates and sends automated email notifications for rental deadlines
3. **Neighborhood Intelligence**: Provides location-based insights using real-time OpenStreetMap data

## Tech Stack

Our RAG-powered property management chatbot leverages a modern, cloud-based architecture designed for scalability, real-time data retrieval, and intelligent document processing.

### Frontend
**Streamlit** - Provides an interactive web interface for the chatbot with minimal development overhead

### Backend & APIs
**FastAPI** - High-performance Python web framework handling API requests, managing chat sessions, and orchestrating communication between components.

**Supabase** - PostgreSQL database with pgvector extension for storing conversation history, user data, and vector embeddings for semantic search. Schema of the tables in the database are described in Appendix (Section 9.1)

### AI & RAG Pipeline
**LlamaIndex** - Manages document indexing, chunking, and retrieval orchestration for the RAG pipeline.

**OpenAI API** - Provides LLM capabilities for natural language understanding and response generation.

Models used:
- `gpt-4o-mini`: Enables the conversational agent and conversation moderation
- `whisper-1`: Enables the voice input features to support accessibility usecases

**Agentic Workflow Router** - Employs intelligent query classification to route requests to specialized tool handlers: lease agreement Q&A for contract inquiries, automated reminder management, and location-based neighborhood search using OpenStreetMap integration.

### Cloud Infrastructure
**Render** - Hosts the FastAPI backend with automatic deployments from Git

**Streamlit Cloud** - Hosts the frontend with automatic deployments from Git

**AWS Services**:
- **EventBridge** - Triggers Lambda on schedule for automated reminders
- **Lambda** - Invokes SES to send reminder emails
- **SES (Simple Email Service)** - Sends transactional email reminders

## Features

### Core Chat Capabilities

#### Text Input Processing
- Conversational interface for user inquiries
- Context-aware responses using RAG

#### Voice Input Accessibility
- Speech-to-Text using Whisper API
- Seamless conversion to text for processing

### Intelligent Query Routing (Agentic Workflow)

The chatbot employs an agentic workflow that automatically classifies user intent and routes queries to specialized tools.

#### Lease Agreement Q&A
- RAG-powered responses from Singapore rental documents
- Provides accurate contract and policy information

#### Reminder Scheduling
- Natural language reminder creation ("remind me about rent on 1st")
- Scheduled email notifications via AWS infrastructure
- List and view active reminders
- Support for 6 reminder types: LOI, Deposit, Lease Signing, Rent Payment, Renewal, Move-out

#### Neighborhood Research
- Location-based POI search using OpenStreetMap
- Finds nearby MRT stations, schools, clinics, markets
- Calculates and displays walking distances from property

### Safety & Security

#### Authentication & Authorization
- JWT-based secure access
- User session management via Supabase
- Role-based access (tenant/property agent)

#### Content Moderation
- Real-time safety checks using OpenAI Moderation API
- Filters inappropriate or harmful content

## How to Run

### Live Application
Visit the deployed application at: **[casa-amigo.streamlit.app](https://casa-amigo.streamlit.app/)**

The app is hosted on Streamlit Cloud with automatic deployments from the main branch.

It is backed up by Render on the backend which is always up and running. 

## How to Develop

### Prerequisites
- Python 3.10 or higher
- OpenAI API key
- Supabase project with API and JWT keys

### Local Setup

1. **Clone and setup environment:**
   ```bash
   git clone https://github.com/s-hreya-riram/casa-amigo.git
   cd casa-amigo
   python -m venv venv
   source ./venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

2. **Configure secrets:**
   ```bash
   cp src/.streamlit/secrets.toml.template src/.streamlit/secrets.toml

   Fill in the required values:
   ```
   [openai]
   api_key = "your-openai-api-key"

   [supabase]
   url = "your-supabase-url"
   key = "your-supabase-anon-key"
   jwt_secret = "your-jwt-secret"
   ```
   Getting your credentials:

   OpenAI API key: platform.openai.com/api-keys
   Supabase credentials: Your project dashboard → Settings → API

3. Run the FastAPI backend:
   ```
   python -m uvicorn main:app --reload
   ```
   The backend will be available at http://localhost:8000
   API Documentation: Visit http://localhost:8000/docs for interactive Swagger documentation

4. Run Streamlit frontend locally:
   ```
   streamlit run src/app.py
   ```

### Development Workflow
* Backend API: Use the FastAPI docs at http://localhost:8000/docs to test endpoints
* Frontend: Streamlit auto-reloads on file changes
* Database: Monitor Supabase dashboard for real-time data changes
* Testing: Both services need to be running for full functionality

### Deployment
Both services deploy automatically:

* Frontend: Streamlit Cloud deploys on Git push to main
* Backend: Render deploys FastAPI service on Git push to main


### Architecture
Casa Amigo follows a cloud-native, microservices architecture:

* Frontend: Streamlit Cloud (auto-deploy from Git)
* Backend: Render FastAPI service (auto-deploy from Git)
* Database: Supabase PostgreSQL with real-time subscriptions
* AI Pipeline: OpenAI + LlamaIndex RAG system
* Notifications: AWS EventBridge → Lambda → SES email pipeline
* Geospatial: OpenStreetMap Overpass API integration

The agentic workflow intelligently routes queries to specialized handlers, making Casa Amigo more than a chatbot—it's a comprehensive Singapore rental intelligence platform.

### Project Structure
## Project Structure

```
casa-amigo/
├── .devcontainer/
│   └── devcontainer.json
│
├── .github/
│   └── workflows/
│       └── keepalive.yml
│
├── .streamlit/
│   └── secrets.toml.template
│
├── assets/                           # Static assets
│   ├── blink_robot_avatar.gif
│   ├── load_robot_avatar.gif
│   ├── logo.png
│   └── user_avatar.png
│
├── data/                             # Document storage
│   ├── contracts/
│   │   └── Track_B_Tenancy_Agreement.pdf
│   └── more_contracts/
│
├── documentation/                    # Project documentation
│   ├── .Rhistory
│   ├── BACKEND_API_DOCUMENTATION.md
│   └── BACKEND_API_TESTING.md
│
├── evaluation/                       # RAG evaluation scripts and results
│   ├── index1_scores/
│   ├── index2_scores/
│   ├── index2_v2_scores/
│   ├── gen_outputs.json
│   ├── generation_eval.py
│   ├── generation_scores.json
│   ├── make_report.py
│   ├── README_EVAL.md
│   ├── retrieval_data.json
│   ├── retrieval_eval.py
│   ├── retrieval_results.json
│   ├── retrieval_scores.json
│   └── rouge_data.json
│
├── pdf_index/                        # Baseline RAG index
│
├── pdf_index_v2/                     # Enhanced RAG index
│   ├── default__vector_store.json
│   ├── docstore.json
│   ├── graph_store.json
│   ├── image_vector_store.json
│   └── index_store.json
│
├── src/                              # Main application code
│   ├── .streamlit/
│   │   ├── config.toml
│   │   └── secrets.toml.template
│   │
│   ├── config/                       # Configuration management
│   │   ├── __init__.py
│   │   └── config_manager.py
│   │
│   ├── core/                         # Core business logic
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── chatbot_engine.py
│   │   └── document_manager.py
│   │
│   ├── entities/                     # Data models (FastAPI)
│   │
│   ├── modules/                      # UI modules
│   │   ├── __init__.py
│   │   └── supabase_instance.py
│   │
│   ├── services/                     # Service layer
│   │   ├── reminders/
│   │   │   ├── __init__.py
│   │   │   └── [reminder services]
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── base.py
│   │   ├── conversation.py
│   │   ├── exceptions.py
│   │   ├── import_properties.py
│   │   ├── pdf_loader.py
│   │   ├── property_service.py
│   │   ├── reminders.py
│   │   ├── schema.py
│   │   ├── scrape_property.py
│   │   ├── tenancy.py
│   │   ├── tenant_profile.py
│   │   ├── user.py
│   │   └── vector_store.py
│   │
│   ├── utils/                        # Utility functions and tools
│   │   ├── __init__.py
│   │   ├── auth_store.py
│   │   ├── current_auth.py
│   │   ├── lease_tool.py
│   │   ├── moderation.py
│   │   ├── neighbourhood_research_tool.py
│   │   ├── prompts.py
│   │   ├── reminder_tool.py
│   │   ├── tool_registry.py
│   │   ├── utils.py
│   │   └── voice.py
│   │
│   ├── .env.example
│   ├── app.py                        # Streamlit frontend entry point
│   ├── doc_run.py
│   ├── main.py                       # FastAPI backend entry point
│   └── role_based_routing.py
│
├── .gitignore
├── app_backup.patch
├── Dockerfile
├── packages.txt
├── pyenv.cfg
├── README.md
├── requirements-render.txt           # Render deployment dependencies
├── requirements.txt                  # Main project dependencies
├── retrieval_scores.json
└── setup.py
```
