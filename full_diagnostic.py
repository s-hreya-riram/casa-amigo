import streamlit as st
import os
import sys
sys.path.append('src')

st.title("🔍 Casa Amigo Deployment Diagnostics")

st.write("### 1. Environment Check")
st.write(f"Python version: {sys.version}")
st.write(f"Current working directory: {os.getcwd()}")
st.write(f"Python path: {sys.path}")

st.write("### 2. Secrets Test")
try:
    api_key = st.secrets["openai"]["api_key"]
    st.success(f"✅ Found API key in secrets: {api_key[:20]}...{api_key[-10:]}")
    st.write(f"Key length: {len(api_key)}")
    st.write(f"Key type: {type(api_key)}")
except Exception as e:
    st.error(f"❌ Secrets error: {e}")
    st.write(f"Error type: {type(e)}")

st.write("### 3. Environment Variables")
env_key = os.getenv("OPENAI_API_KEY")
if env_key:
    st.info(f"✅ Environment key: {env_key[:20]}...{env_key[-10:]}")
else:
    st.warning("⚠️ No environment variable found")

st.write("### 4. ConfigManager Test")
try:
    from config.config_manager import ConfigManager
    st.info("✅ ConfigManager imported successfully")
    
    # Test initialization
    config = ConfigManager()
    st.success("✅ ConfigManager initialized")
    st.write(f"API key loaded: {config.api_key[:20] if config.api_key else 'None'}...")
    
except Exception as e:
    st.error(f"❌ ConfigManager error: {e}")
    st.write(f"Error type: {type(e)}")
    import traceback
    st.code(traceback.format_exc())

st.write("### 5. File System Check")
st.write("Files in current directory:")
for item in os.listdir('.'):
    st.write(f"- {item}")

st.write("Files in src directory:")
try:
    for item in os.listdir('src'):
        st.write(f"- src/{item}")
except Exception as e:
    st.error(f"Can't list src directory: {e}")

st.write("### 6. Secrets File Check")
secrets_paths = [
    '.streamlit/secrets.toml',
    'secrets.toml',
    '.streamlit/secrets.json'
]

for path in secrets_paths:
    if os.path.exists(path):
        st.success(f"✅ Found: {path}")
    else:
        st.warning(f"⚠️ Not found: {path}")

st.write("### 7. Import Test")
try:
    import openai
    st.success("✅ OpenAI library imported")
    st.write(f"OpenAI version: {openai.__version__}")
except Exception as e:
    st.error(f"❌ OpenAI import error: {e}")

st.write("### 8. Full App Test")
try:
    from config import ConfigManager
    from core import ChatbotEngine, DocumentIndexManager
    
    st.info("✅ All imports successful")
    
    # Test full initialization
    config_manager = ConfigManager()
    st.success(f"✅ ConfigManager: API key loaded ({config_manager.api_key[:20] if config_manager.api_key else 'None'}...)")
    
    doc_manager = DocumentIndexManager()
    st.success("✅ DocumentIndexManager initialized")
    
    chatbot = ChatbotEngine(doc_manager.index, config_manager.api_key)
    st.success("✅ ChatbotEngine initialized")
    
except Exception as e:
    st.error(f"❌ Full app test error: {e}")
    import traceback
    st.code(traceback.format_exc())
