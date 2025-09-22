# CasaAmigo

Repository for a tenant services chatbot

## Setup

- Ensure you have Python (3.10 or higher) and virtual environment set up
If you have an older version of Python and install a new version, make sure you run `python --version` from your virtual environment to ensure that the Python version used is the latest version otherwise your app deployment could have errors.
- Proceed to run `python -m venv venv` followed by `source ./venv/bin/activate` (or `venv\Scripts\activate` for Windows) from your workspace
- Once you have the virtual environment activated, run `pip install -r requirements.txt` (initial installation of dependencies could take a couple of minutes). Please do not install any dependencies manually as that could conflict with the dependencies in requirements.txt
- Create a .env file in the directory with your OpenAI key


## Testing

- If you want to ensure your changes are working fine, execute `streamlit run app.py` to test the changes on the Streamlit app
