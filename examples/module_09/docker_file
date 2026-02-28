# Dockerfile for examples/module_09/
#
# Claude generated this file from the prompt:
#   "Create a Dockerfile for a Python 3.11 app in the DisSysLab repo.
#    The app is examples/module_09/app.py. It needs websocket-client
#    and anthropic. Install only what the app needs, not the full
#    dev requirements."
#
# You do not need to understand Docker to use this file.
# The README explains what each line does.

# 1. Start from an official Python image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install only what this app needs (not the full dev requirements)
RUN pip install --no-cache-dir \
    anthropic>=0.39.0 \
    python-dotenv>=1.0.0 \
    feedparser>=6.0.11 \
    websocket-client>=1.6.0

# 4. Copy the rest of the project into the container
COPY . .

# 5. Run the app when the container starts
CMD ["python3", "-m", "examples.module_09.app"]