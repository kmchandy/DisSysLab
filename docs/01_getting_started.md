# Getting Started

Welcome to **DisSysLab**, a lightweight framework for building and experimenting with distributed systems using stream-based agents and networks. This guide walks you through setting up your environment, running your first network, and understanding the core ideas behind the framework.

## 🚀 Installation

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
pip install -e .

## 🔑 Setting Up OpenAI Credentials (Optional)

If you plan to use OpenAI tools in your agents:

1. Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

2. Open the new `.env` file and paste your OpenAI API key:
    ```bash
    OPENAI_API_KEY=your-api-key-here
    ```

3. Test that it works:
    ```bash
    python -c "from get_credentials import get_openai_client; get_openai_client(verbose=True)"
    ```