FROM python:3.11-slim

# 1. Set the top-level project directory as the WORKDIR
WORKDIR /app

# 2. Copy dependencies and install them
# Copy requirements.txt to /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the entire repository content (including the 'src' folder)
# This places src/main.py at /app/src/main.py
COPY . .

# 4. Expose the port
EXPOSE 8000

# 5. Crucial Fix: Add /app to the Python path and execute the app
# By setting PYTHONUNBUFFERED=1, we get real-time logs.
# By setting PYTHONPATH=., we tell Python to look for modules starting in /app (the WORKDIR).
# The CMD then correctly runs the app using the full module path: src.main:app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]