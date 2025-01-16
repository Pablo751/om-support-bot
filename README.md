# YOM Support Bot

WhatsApp support bot for YOM using FastAPI and OpenAI GPT.

## Features

- WhatsApp message handling via webhook
- Store status checking with MongoDB integration
- Knowledge base-driven responses
- OpenAI GPT for natural language understanding
- Automatic response generation

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/yom-support-bot.git
cd yom-support-bot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Run the application:
```bash
python -m uvicorn src.main:app --reload
```

## Environment Variables

Required environment variables:
- `WASAPI_API_KEY`: WhatsApp API key
- `OPENAI_API_KEY`: OpenAI API key
- `MONGO_PASSWORD`: MongoDB password

## API Endpoints

- `POST /webhook`: Handle incoming WhatsApp messages
- `GET /health`: Health check endpoint

## Deployment

The application is configured for deployment on Railway.

1. Push to GitHub
2. Connect your GitHub repository to Railway
3. Set up environment variables in Railway dashboard
4. Deploy!