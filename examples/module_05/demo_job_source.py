# examples/module_05/demo_job_source.py

"""
Demo job postings for Module 05.

This file defines DEMO_JOB_FEEDS — a dict of fake job posting feeds that
mirror the structure of DemoRSSSource. Students can run app.py without any
API keys or network access.

Each entry is a list of strings simulating real job posting titles/summaries
from that feed, including a mix of relevant matches and irrelevant posts so
that the keyword filter has something interesting to do.
"""

DEMO_JOB_FEEDS = {
    "python_jobs": [
        "Senior Python Engineer at Stripe — Remote, $180k-$220k",
        "Python Backend Developer at Airbnb — San Francisco, relocation provided",
        "Java Developer at Oracle — Austin TX, on-site required",
        "Python Data Engineer at Spotify — NYC or Remote, $160k",
        "CLICK HERE to get rich quick — work from home guaranteed income!!!",
        "Machine Learning Engineer (Python) at OpenAI — San Francisco",
        "PHP Web Developer at legacy fintech startup — on-site only",
        "Python API Developer at Twilio — Remote-friendly, $140k-$170k",
        "Ruby on Rails Engineer at Basecamp — fully remote",
        "Staff Python Engineer at Anthropic — San Francisco, $200k-$250k",
        "Junior Python Developer at local agency — part time, unpaid trial",
        "Python Automation Engineer at Tesla — Fremont CA, $150k",
        "BUY NOW! Make $5000/week with our automated trading bot!",
        "Python DevOps Engineer at GitHub — Remote, $170k-$190k",
        "C++ Systems Engineer at NVIDIA — Santa Clara, relocation package",
    ],
    "ml_jobs": [
        "ML Engineer (Python/PyTorch) at DeepMind — London or Remote",
        "Research Scientist at Meta AI — Menlo Park, $200k+",
        "URGENT: Work from home, no experience needed, $1000/day guaranteed",
        "Applied ML Engineer at Google Brain — Mountain View, competitive",
        "Data Scientist (Python/SQL) at Airbnb — Remote, $165k",
        "AI Researcher at Cohere — Toronto or Remote, equity + salary",
        "Machine Learning Platform Engineer at Lyft — San Francisco",
        "NLP Engineer at Hugging Face — Remote worldwide, $140k-$180k",
        "FREE MONEY: Refer friends and earn passive income today!!!",
        "Computer Vision Engineer at Tesla Autopilot — Austin TX",
        "MLOps Engineer at Netflix — Los Gatos CA or Remote, $180k",
        "Reinforcement Learning Researcher at DeepMind — Paris",
        "Data Engineer at Snowflake — Remote US, $155k-$175k",
        "AI Safety Researcher at Anthropic — San Francisco, mission-driven",
        "Get paid to take surveys!!! No skills needed, $500/day",
    ],
}
