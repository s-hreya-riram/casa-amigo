#!/usr/bin/env python3
"""
Casa Amigo Setup Script
Helps configure Streamlit secrets for the application
"""

import os
import shutil
from pathlib import Path

def setup_streamlit_secrets():
    """Setup Streamlit secrets configuration."""
    print("🏠 Casa Amigo Setup Script")
    print("=" * 40)
    
    # Check if .streamlit directory exists
    streamlit_dir = Path(".streamlit")
    if not streamlit_dir.exists():
        print("📁 Creating .streamlit directory...")
        streamlit_dir.mkdir()
    
    secrets_file = streamlit_dir / "secrets.toml"
    template_file = streamlit_dir / "secrets.toml.template"
    
    # Check if secrets.toml already exists
    if secrets_file.exists():
        overwrite = input("⚠️  secrets.toml already exists. Overwrite? (y/N): ")
        if overwrite.lower() != 'y':
            print("❌ Setup cancelled.")
            return
    
    # Copy template if it doesn't exist
    if not template_file.exists():
        print("❌ Template file not found. Please run this from the project root.")
        return
    
    # Copy template to secrets.toml
    print("📄 Copying template to secrets.toml...")
    shutil.copy(template_file, secrets_file)
    
    # Get OpenAI API key from user
    print("\n🔑 OpenAI API Key Configuration")
    print("You can get your API key from: https://platform.openai.com/api-keys")
    
    api_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
    
    if api_key:
        # Update the secrets file with the actual API key
        with open(secrets_file, 'r') as f:
            content = f.read()
        
        content = content.replace('api_key = "your_openai_api_key_here"', f'api_key = "{api_key}"')
        
        with open(secrets_file, 'w') as f:
            f.write(content)
        
        print("✅ API key configured successfully!")
    else:
        print("⏩ Skipping API key configuration. You can edit .streamlit/secrets.toml manually.")
    
    print("\n🎉 Setup complete!")
    print("📝 Next steps:")
    print("1. Edit .streamlit/secrets.toml if you skipped API key configuration")
    print("2. Run: streamlit run src/app.py")
    print("3. Your secrets are automatically ignored by git for security")

if __name__ == "__main__":
    setup_streamlit_secrets()
