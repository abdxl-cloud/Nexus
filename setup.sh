#!/bin/bash

# Suna Lite Setup Script
# Automatically clones CoexistAI and sets up the complete environment

set -e

echo "🚀 Setting up Suna Lite with CoexistAI..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists git; then
    echo "❌ Git is required but not installed. Please install git first."
    exit 1
fi

if ! command_exists docker; then
    echo "❌ Docker is required but not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose || ! command_exists docker; then
    echo "❌ Docker Compose is required but not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Clone CoexistAI if it doesn't exist
if [ ! -d "coexistai" ]; then
    echo "📥 Cloning CoexistAI repository..."
    git clone https://github.com/SPThole/CoexistAI.git coexistai
    echo "✅ CoexistAI cloned successfully"
else
    echo "✅ CoexistAI directory already exists"
    echo "🔄 Pulling latest changes..."
    cd coexistai && git pull && cd ..
fi

# Copy the Dockerfile template to CoexistAI directory
echo "🐳 Setting up CoexistAI Docker configuration..."
cat > coexistai/Dockerfile << 'DOCKERFILE_CONTENT'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for builds + curl for healthcheck
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl git build-essential gcc g++ \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements if present, install
COPY requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip \
 && if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      pip install --no-cache-dir \
        fastapi==0.104.1 \
        uvicorn[standard]==0.24.0 \
        httpx==0.25.2 \
        python-dotenv==1.0.0 \
        requests==2.31.0 \
        beautifulsoup4==4.12.2 \
        lxml==4.9.3 \
        aiofiles==23.2.1 \
        pydantic==2.5.0 \
        pydantic-settings==2.0.3; \
    fi

# Copy app
COPY . .

# Create a minimal app.py ONLY if missing (no heredoc)
RUN [ -f app.py ] || printf "%s\n" \
  "from fastapi import FastAPI" \
  "import os" \
  "" \
  "app = FastAPI(title='CoexistAI', version='1.0.0')" \
  "" \
  "@app.get('/health')" \
  "async def health_check():" \
  "    return {'status': 'healthy', 'service': 'coexistai'}" \
  "" \
  "@app.post('/web-search')" \
  "async def web_search(request: dict):" \
  "    query = request.get('query', '')" \
  "    return {'query': query, 'results': [{'title': f'Search result for: {query}', 'url': 'https://example.com', 'snippet': f\"This is a search result for '{query}' (CoexistAI stub)\"}], 'source': 'coexistai-stub'}" \
  "" \
  "@app.get('/')" \
  "async def root():" \
  "    return {'message': 'CoexistAI Service', 'version': '1.0.0'}" \
  "" \
  "if __name__ == '__main__':" \
  "    import uvicorn" \
  "    uvicorn.run(app, host='0.0.0.0', port=8000)" \
  > app.py

# Non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
DOCKERFILE_CONTENT

# Create basic model_config.py for CoexistAI
echo "⚙️ Setting up CoexistAI configuration..."
cat > "coexistai/model_config.py" << 'EOF'
import os

# Get API keys from environment
openai_api_key = os.getenv("OPENAI_API_KEY", "")
google_api_key = os.getenv("GOOGLE_API_KEY", "")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

# Choose the best available model
if openai_api_key:
    llm_type = "openai"
    llm_model = "gpt-3.5-turbo"
    api_key = openai_api_key
elif google_api_key:
    llm_type = "google"
    llm_model = "gemini-1.5-flash"
    api_key = google_api_key
elif anthropic_api_key:
    llm_type = "anthropic"
    llm_model = "claude-3-haiku-20240307"
    api_key = anthropic_api_key
else:
    # Fallback to mock/local mode
    llm_type = "local"
    llm_model = "mock-model"
    api_key = ""

model_config = {
    "llm_model_name": llm_model,
    "llm_type": llm_type,
    "llm_tools": None,
    "llm_kwargs": {
        "temperature": 0.1,
        "max_tokens": None,
        "timeout": None,
        "max_retries": 2,
        "api_key": api_key,
    },
    "embedding_model_name": "text-embedding-ada-002" if openai_api_key else "nomic-ai/nomic-embed-text-v1",
    "embed_kwargs": {},
    "embed_mode": "openai" if openai_api_key else "infinity_emb",
    "cross_encoder_name": "BAAI/bge-reranker-base"
}

print(f"CoexistAI configured with LLM type: {llm_type}, model: {llm_model}")
EOF

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys:"
    echo "   - OPENAI_API_KEY=your_key_here"
    echo "   - TAVILY_API_KEY=your_key_here" 
    echo "   - GOOGLE_API_KEY=your_key_here"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Check if we have any API keys set (with better error handling)
echo "🔑 Checking API key configuration..."
if [ -f ".env" ]; then
    # Check if .env file is valid by trying to parse it safely
    if ! grep -q "^[A-Z_]*=" .env 2>/dev/null; then
        echo "⚠️  .env file exists but may have syntax issues"
        echo "🔧 You may need to fix the .env file manually"
    else
        # Use a safer method to check for API keys
        api_key_count=0
        
        if grep -q "^OPENAI_API_KEY=.*[^=]" .env; then
            if ! grep -q "^OPENAI_API_KEY=your_openai_api_key_here" .env; then
                echo "✅ OpenAI API key configured"
                ((api_key_count++))
            fi
        fi
        
        if grep -q "^TAVILY_API_KEY=.*[^=]" .env; then
            if ! grep -q "^TAVILY_API_KEY=your_tavily_api_key_here" .env; then
                echo "✅ Tavily API key configured"
                ((api_key_count++))
            fi
        fi
        
        if grep -q "^GOOGLE_API_KEY=.*[^=]" .env; then
            if ! grep -q "^GOOGLE_API_KEY=your_google_api_key_here" .env; then
                echo "✅ Google API key configured"
                ((api_key_count++))
            fi
        fi
        
        if grep -q "^ANTHROPIC_API_KEY=.*[^=]" .env; then
            if ! grep -q "^ANTHROPIC_API_KEY=your_anthropic_api_key_here" .env; then
                echo "✅ Anthropic API key configured"
                ((api_key_count++))
            fi
        fi
        
        if [ $api_key_count -eq 0 ]; then
            echo "⚠️  No API keys configured - system will use stub/mock responses"
        else
            echo "✅ $api_key_count API key(s) configured"
        fi
    fi
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys (optional but recommended)"
echo "2. Start the services:"
echo "   make up"
echo ""
echo "3. Test the API:"
echo "   python test_api.py"
echo ""
echo "Services will be available at:"
echo "   - Main API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - CoexistAI: http://localhost:8001"
echo "   - Runner: http://localhost:8080"
echo ""
echo "🔧 For development mode (without Docker):"
echo "   make dev"