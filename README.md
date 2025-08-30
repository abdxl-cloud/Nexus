# Suna Lite Agent

A minimal, runnable MVP implementation of a "Suna-like" AI agent with ReAct-style orchestration, web search capabilities via CoexistAI, and streaming responses.

## Features

- **ReAct-Style Agent Loop**: Simple reasoning and acting loop without complex frameworks
- **Streaming Responses**: Real-time Server-Sent Events (SSE) for live agent interactions
- **CoexistAI Integration**: Web search powered by CoexistAI with automatic setup
- **Tool Integration**: Web search and browser tools (with stubs for easy extension)
- **PostgreSQL Database**: Persistent conversation and session storage
- **FastAPI Backend**: Modern, fast web framework with automatic API documentation
- **Docker Support**: Easy deployment with Docker Compose
- **Automated Setup**: One-command setup that clones and configures CoexistAI

## Quick Start (Recommended)

### Automated Setup with CoexistAI

```bash
# Clone the repository
git clone <your-repo-url>
cd suna_lite

# Run automated setup (clones CoexistAI, configures everything)
make up

# This automatically:
# 1. Clones CoexistAI repository
# 2. Creates proper Docker configuration
# 3. Sets up all services
# 4. Starts the complete stack
```

### Manual Setup (Alternative)

```bash
# 1. Run setup script manually
chmod +x setup.sh
./setup.sh

# 2. Configure API keys in .env (optional but recommended)
cp .env.example .env
# Edit .env and add your API keys

# 3. Start services
make up
```

### Services Available

After running `make up`, you'll have:

- **Main API**: http://localhost:8000 (Suna Lite Agent)
- **API Documentation**: http://localhost:8000/docs
- **CoexistAI**: http://localhost:8001 (Web Search Service)
- **Runner**: http://localhost:8080 (Browser Automation)
- **PostgreSQL**: localhost:5432 (Database)

## API Usage

### Basic Workflow

```bash
# 1. Create a new thread
curl -X POST http://localhost:8000/api/threads \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# 2. Send a message and start a run
curl -X POST http://localhost:8000/api/threads/{thread_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Search for the latest AI news"}'

# 3. Stream the run events (SSE)
curl -N http://localhost:8000/api/runs/{run_id}/events
```

### Testing the Setup

```bash
# Run the included test script
python test_api.py
```

## Configuration

### API Keys (Optional but Recommended)

Edit the `.env` file to add your API keys for enhanced functionality:

```bash
# For real web search (choose one):
TAVILY_API_KEY=your_tavily_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database (already configured)
DATABASE_URL=postgresql://postgres:password@localhost:5432/suna_lite
```

**Without API keys**: The system will work with stub/mock responses for web search.

## Project Structure

```
suna_lite/
├── setup.sh               # 🆕 Automated setup script
├── backend/
│   ├── app.py              # FastAPI application entry point
│   ├── config.py           # Configuration and environment variables
│   ├── agent/
│   │   ├── loop.py         # ReAct-style agent orchestration
│   │   ├── memory.py       # Conversation memory management
│   │   └── tools/
│   │       ├── web_search.py  # Web search tool (CoexistAI integration)
│   │       └── browser.py     # Browser automation tool
│   ├── db/
│   │   ├── models.py       # SQLAlchemy database models
│   │   └── schema.sql      # PostgreSQL database schema
│   └── api/
│       ├── routes.py       # API endpoints with SSE streaming
│       └── utils.py        # API utility functions
├── docker/
│   └── runner/
│       └── Dockerfile      # Browser automation container
├── coexistai/              # 🆕 Auto-cloned CoexistAI repository
│   ├── app.py              # CoexistAI main application
│   ├── Dockerfile          # 🆕 Auto-generated Dockerfile
│   └── model_config.py     # 🆕 Auto-generated configuration
├── docker-compose.yml      # 🆕 Enhanced with CoexistAI service
├── Makefile               # 🆕 Enhanced with setup target
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── test_api.py            # API testing script
```

## Development Commands

```bash
# Setup and start everything
make up

# Development mode (local, no Docker)
make dev

# View logs
make logs

# Stop services
make down

# Clean up completely
make clean

# Test the API
make test

# Check service health
make health
```

## How the Automated Setup Works

The enhanced setup process:

1. **Checks Prerequisites**: Verifies Git, Docker, and Docker Compose are installed
2. **Clones CoexistAI**: Automatically downloads the latest CoexistAI from GitHub
3. **Creates Docker Configuration**: Generates proper Dockerfile for CoexistAI
4. **Sets Up Configuration**: Creates model_config.py with smart API key detection
5. **Configures Health Checks**: Adds proper health endpoints for Docker
6. **Creates .env Template**: Sets up environment configuration if needed

## API Endpoints

### Core Endpoints

- `POST /api/threads` - Create a new conversation thread
- `POST /api/threads/{thread_id}/messages` - Send message and start run
- `GET /api/runs/{run_id}/events` - Stream run events via SSE
- `GET /health` - Health check for all services

### Server-Sent Events (SSE) Format

```
event: message
data: {"type": "message", "content": "I will search for AI news..."}

event: tool
data: {"type": "tool", "name": "web_search", "args": {"query": "latest AI news"}}

event: token
data: {"type": "token", "data": "Based on my search..."}

event: done
data: {"type": "run_completed", "status": "completed"}
```

## CoexistAI Integration

The system automatically sets up CoexistAI with:

- **Smart API Key Detection**: Uses OpenAI, Google, or Anthropic keys automatically
- **Fallback Mode**: Works with stub responses if no API keys provided
- **Health Monitoring**: Proper Docker health checks
- **Auto-Configuration**: Generates optimal configuration based on available keys

### Getting Real Search Results

To get actual web search results, add any of these API keys to your `.env` file:

```bash
# Option 1: Tavily (recommended for search)
TAVILY_API_KEY=your_tavily_key

# Option 2: OpenAI
OPENAI_API_KEY=your_openai_key

# Option 3: Google AI
GOOGLE_API_KEY=your_google_key

# Option 4: Anthropic
ANTHROPIC_API_KEY=your_anthropic_key
```

## Troubleshooting

### Common Issues

1. **Git not found**
   ```bash
   # Install git first
   sudo apt update && sudo apt install git
   ```

2. **Docker permission denied**
   ```bash
   # Add user to docker group
   sudo usermod -aG docker $USER
   # Log out and back