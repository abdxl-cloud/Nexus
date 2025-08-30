# Suna Lite Agent

A minimal, runnable MVP implementation of a "Suna-like" AI agent with ReAct-style orchestration, web search capabilities via CoexistAI, and streaming responses.

## Features

- **ReAct-Style Agent Loop**: Simple reasoning and acting loop without complex frameworks
- **Streaming Responses**: Real-time Server-Sent Events (SSE) for live agent interactions
- **CoexistAI Integration**: Web search powered by CoexistAI with fallback stub implementation
- **Tool Integration**: Web search and browser tools (with stubs for easy extension)
- **PostgreSQL Database**: Persistent conversation and session storage
- **FastAPI Backend**: Modern, fast web framework with automatic API documentation
- **Docker Support**: Easy deployment with Docker Compose
- **Development Tools**: Makefile targets for common development tasks

## Quick Start

### Option 1: Docker (with bundled CoexistAI)

```bash
# Start all services including CoexistAI
# Set TAVILY_API_KEY for real web search results
export TAVILY_API_KEY=your_tavily_api_key
make up

# The API will be available at:
# - Main API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Health Check: http://localhost:8000/health
# - CoexistAI: http://localhost:8001
```

### Option 2: Docker with Remote CoexistAI

```bash
# Set COEXISTAI_BASE_URL (and optionally COEXISTAI_API_KEY) to your hosted instance
export COEXISTAI_BASE_URL=https://your-coexistai-instance.com
# export COEXISTAI_API_KEY=your_api_key

# Start services
make up
```

### Option 3: Local Development

```bash
# Run the API locally (without Docker)
make dev
```

## API Usage

### Basic API Endpoints

```bash
# Create a new thread
curl -X POST http://localhost:8000/threads \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# Send a message and start a run
curl -X POST http://localhost:8000/threads/{thread_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Search for the latest AI news"}'

@@ -68,75 +68,65 @@ curl -N http://localhost:8000/runs/{run_id}/events
```

### Server-Sent Events (SSE) Format

The `/runs/{run_id}/events` endpoint streams events in the following format:

```
event: message
data: {"type": "message", "content": "I will search for AI news..."}

event: tool
data: {"type": "tool", "name": "web_search", "args": {"query": "latest AI news"}}

event: token
data: {"type": "token", "data": "Based on my search..."}

event: heartbeat
data: {"type": "heartbeat", "timestamp": 1703123456}

event: done
data: {"type": "run_completed", "status": "completed"}
```

## CoexistAI Integration

**Important**: This agent uses CoexistAI for web search functionality. The Docker setup starts a CoexistAI container automatically using the published `spthole/coexistai` image.

To get real search results, set the `TAVILY_API_KEY` environment variable before running `make up`:

```bash
export TAVILY_API_KEY=your_tavily_api_key
make up
```

If you want to use a hosted CoexistAI instance instead, set `COEXISTAI_BASE_URL` (and optionally `COEXISTAI_API_KEY`) before starting the services:

```bash
export COEXISTAI_BASE_URL=https://your-coexistai-instance.com
# export COEXISTAI_API_KEY=your_api_key
make up
```

**Note**: If CoexistAI is not available, the agent will fall back to a stub implementation that returns mock search results.

## Project Structure

```
suna_lite/
├── backend/
│   ├── app.py              # FastAPI application entry point
│   ├── config.py           # Configuration and environment variables
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── loop.py         # ReAct-style agent orchestration
│   │   ├── memory.py       # Conversation memory management
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── web_search.py  # Web search tool (CoexistAI integration)
│   │       └── browser.py     # Browser automation tool
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py       # SQLAlchemy database models
│   │   └── schema.sql      # PostgreSQL database schema
│   └── api/
│       ├── __init__.py
│       └── routes.py       # API endpoints with SSE streaming
├── docker/
│   └── runner/
│       └── Dockerfile      # Application container
├── docker-compose.yml      # Multi-service orchestration
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── README.md              # This file
└── Makefile              # Development automation
```

## API Endpoints

### Core Endpoints

- `POST /api/chat` - Non-streaming chat endpoint
- `POST /api/chat/stream` - Streaming chat with Server-Sent Events
- `GET /api/conversations/{session_id}` - Get conversation history
- `GET /api/agents` - List available agents
- `GET /api/tools` - List available tools
- `GET /health` - Health check
- `GET /api/status` - System status

### Example Usage

#### Non-streaming Chat

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather like today?",
    "session_id": "test-session-123"
  }'
```

#### Streaming Chat

```bash
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for recent AI developments",
    "session_id": "test-session-456"
  }'
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required for web search functionality
TAVILY_API_KEY=your_tavily_api_key_here

# Database connection
DATABASE_URL=postgresql://postgres:password@localhost:5432/suna_lite

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### API Keys

- **Tavily API**: Get your key from [tavily.com](https://tavily.com) for web search functionality
- **OpenAI API**: Optional, for future LLM integration

## Development

### Available Make Commands

```bash
# Development
make dev         # Run app locally (without docker)
make up          # Docker compose up --build
make down        # Docker compose down -v
make logs        # Docker compose logs -f api
```

### Database Schema

The application uses PostgreSQL with the following main tables:

- `agents` - Agent configurations
- `conversations` - Chat sessions
- `messages` - Individual messages
- `sessions` - User session tracking

### Adding New Tools

1. Create a new tool class in `backend/agent/tools/`
2. Implement the `execute()` method and `get_tool_info()`
3. Register the tool in `backend/agent/loop.py`
4. Update the tool imports in `backend/agent/tools/__init__.py`

Example tool structure:

```python
class MyTool:
    def __init__(self):
        self.name = "my_tool"
        self.description = "Description of what this tool does"
    
    async def execute(self, **kwargs):
        # Tool implementation
        return {"status": "success", "result": "..."}
    
    def get_tool_info(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {...}
        }
```

## Architecture

### Agent Loop (ReAct Style)

The agent follows a simple ReAct (Reasoning + Acting) pattern:

1. **Think**: Analyze the current context and decide what to do
2. **Act**: Execute a tool or action based on the thought
3. **Observe**: Process the results and update memory
4. **Repeat**: Continue until the task is complete

### Streaming Implementation

The application uses Server-Sent Events (SSE) for real-time streaming:

- Each agent step is streamed as a separate event
- Events include thoughts, actions, and results
- Frontend can display progress in real-time

### Memory Management

Conversation memory is handled at two levels:

- **In-Memory**: Fast access during agent execution
- **Database**: Persistent storage for conversation history

## Deployment

### Production Deployment

1. Set up a PostgreSQL database
2. Configure environment variables
3. Build and deploy the Docker container
4. Set up a reverse proxy (nginx) for HTTPS

### Environment Variables for Production

```bash
DEBUG=false
DATABASE_URL=postgresql://user:pass@prod-db:5432/suna_lite
TAVILY_API_KEY=your_production_api_key
SECRET_KEY=your_secure_secret_key
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   make db-up
   # Wait for database to be ready
   make health
   ```

2. **Port Already in Use**
   ```bash
   # Change PORT in .env file or stop conflicting service
   lsof -i :8000
   ```

3. **Missing API Keys**
   - Web search will return mock data without TAVILY_API_KEY
   - Check `.env` file configuration

### Logs

```bash
# View application logs
make docker-logs

# View specific service logs
docker-compose logs app
docker-compose logs postgres
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `make test lint`
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Roadmap

- [ ] LLM integration (OpenAI, Anthropic)
- [ ] Enhanced browser automation with Playwright
- [ ] Redis caching layer
- [ ] Authentication and user management
- [ ] Plugin system for custom tools
- [ ] Web interface for agent interactions
- [ ] Advanced memory and context management
- [ ] Multi-agent orchestration