# Casa Amigo 🏠

Casa Amigo is a tenant assistant Streamlit app aimed at reducing time spent by property managers to answer redundant questions from prospective/existing tenants while ensuring an excellent experience for tenants. 

## What it does

Casa Amigo uses AI to help tenants understand their rental agreements without reading through dense legal documents. Here's how it works:

1. **Document Processing**: The system reads and processes rental documents from a curated corpus using PyPDF and document parsing tools
2. **Vector Indexing**: LlamaIndex converts these documents into searchable vector store indices, allowing for semantic similarity searches
3. **Intelligent Retrieval**: When you ask a question, the system searches the vector indices to find relevant document sections
4. **Contextual Response**: GPT-4o-mini uses the retrieved document sections as context to generate accurate, document-grounded responses through RAG
5. **Memory Buffer**: Your conversation history is stored in a memory buffer, allowing the AI to maintain context across multiple questions

The app is specifically tailored for Singapore's rental market, including HDB regulations and expat-specific requirements but can be extended to global markets with the inclusion of the relevant corpus.

## Tech Stack

- **Frontend**: Streamlit
- **AI/ML**: OpenAI GPT-4o-mini, LlamaIndex for document retrieval
- **Database**: SQLite (dev) / PostgreSQL (prod) with SQLAlchemy
- **Document Processing**: PyPDF, python-docx

## Getting Started

### Prerequisites
- Python 3.10 or higher
- OpenAI API key
- Supabase API and JWT keys

### Installation

1. Clone the repository and navigate to the project directory

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source ./venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your credentials using Streamlit secrets (frontend-related) and (or) your .env (backend-related):

   Locate the OpenAI API key in https://platform.openai.com/settings/organization/api-keys, 
   the project_name from https://supabase.com/dashboard/project/upendnxzcnatkvlmkkfn/settings/general (look for projectID),
   the Supabase API credentials in 
   https://supabase.com/dashboard/project/upendnxzcnatkvlmkkfn/settings/api-keys
   ```

### Streamlit Cloud Deployment
   When deploying to Streamlit Cloud:
   1. Go to your app dashboard on [share.streamlit.io](https://share.streamlit.io)
   2. Click on your app, then navigate to "Settings" → "Secrets"
   3. Add the same configurations you added in Step 4 of ## Installation in the secrets editor
   4. Click "Save" and wait for automatic redeployment
   
   ⚠️ **Important**: Make sure to include the section headers like `[openai]` - this is required for the app to find your API key in Streamlit Cloud.

5. Run the application locally :
   ```bash
   streamlit run src/app.py
   ```

The app will open in your browser.

## Project Structure

```
src/
├── app.py              # Main Streamlit application
├── config/             # Configuration management
├── core/               # Core business logic (chatbot, document processing)
├── models/             # Database models
├── services/           # Additional services (reminders, etc.)
└── utils/              # Utility functions

data/                   # Sample rental documents for testing
```

## Upcoming Features

Casa Amigo is continuously evolving with new capabilities in development:

### **Smart Notifications & Reminders**
- Automated rent due alerts via email and browser notifications
- Lease renewal warnings with advance notice
- Important date tracking extracted from documents
- Calendar integration for rental milestones

### **Enhanced User Experience**
- User authentication and personalized accounts
- Secure login functionality with password hashing
- Individual chat history and session management
- Multi-language support (Chinese/Malay translations)
