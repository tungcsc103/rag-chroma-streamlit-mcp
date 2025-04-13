#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0 # Port is in use
    else
        return 1 # Port is free
    fi
}

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
else
    echo -e "${BLUE}No .env file found, using environment variables or defaults${NC}"
fi

# Set default values if not in .env
API_PORT=${API_PORT:-8001}
API_HOST=${API_HOST:-0.0.0.0}
STREAMLIT_PORT=${STREAMLIT_PORT:-8501}

# In Docker, we don't need to check ports as they're managed by Docker
if [ -z "$DOCKER_CONTAINER" ]; then
    if check_port $API_PORT; then
        echo -e "${RED}Error: Port $API_PORT is already in use. Please choose a different port or stop the existing process.${NC}"
        exit 1
    fi
fi

# Ensure data directory exists and has correct permissions
mkdir -p "$SCRIPT_DIR/data/chroma"
chmod -R 777 "$SCRIPT_DIR/data/chroma"

# Function to start FastAPI server
start_api() {
    echo -e "${GREEN}Starting FastAPI server on $API_HOST:$API_PORT...${NC}"
    uvicorn src.api.main:app --host $API_HOST --port $API_PORT --reload > "$SCRIPT_DIR/logs/api.log" 2>&1 &
    API_PID=$!
    echo $API_PID > "$SCRIPT_DIR/logs/api.pid"
    echo -e "${GREEN}FastAPI server started with PID: $API_PID${NC}"
}

# Function to start Streamlit app
start_streamlit() {
    echo -e "${BLUE}Starting Streamlit app...${NC}"
    streamlit run src/app.py --server.port $STREAMLIT_PORT --server.address $API_HOST > "$SCRIPT_DIR/logs/streamlit.log" 2>&1 &
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > "$SCRIPT_DIR/logs/streamlit.pid"
    echo -e "${BLUE}Streamlit app started with PID: $STREAMLIT_PID${NC}"
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${RED}Shutting down servers...${NC}"
    if [ -f "$SCRIPT_DIR/logs/api.pid" ]; then
        kill $(cat "$SCRIPT_DIR/logs/api.pid") 2>/dev/null
        rm "$SCRIPT_DIR/logs/api.pid"
    fi
    if [ -f "$SCRIPT_DIR/logs/streamlit.pid" ]; then
        kill $(cat "$SCRIPT_DIR/logs/streamlit.pid") 2>/dev/null
        rm "$SCRIPT_DIR/logs/streamlit.pid"
    fi
    echo -e "${GREEN}Servers stopped${NC}"
    exit 0
}

# Set up trap for cleanup on script termination
trap cleanup SIGINT SIGTERM

# Kill any existing processes on ports 8000, 8001, and 8501
echo "Cleaning up existing processes..."

lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null

# Export environment variables
export CHROMA_HOST="localhost"
export CHROMA_PORT="8000"
export API_HOST="localhost"
export API_PORT="8001"
export EMBEDDING_MODEL="BAAI/bge-base-en-v1.5"

# Start backend service in the background
echo "Starting backend service..."
cd src
PYTHONPATH=. python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8001 &
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Start frontend service
echo "Starting frontend service..."
cd src
PYTHONPATH=. streamlit run app.py --server.port 8501

# Start servers
start_api
sleep 2 # Wait for API to start
start_streamlit

# Print access URLs
echo -e "\n${GREEN}Services started:${NC}"
echo -e "FastAPI server: ${BLUE}http://$API_HOST:$API_PORT${NC}"
echo -e "Streamlit app:  ${BLUE}http://$API_HOST:$STREAMLIT_PORT${NC}"
echo -e "\n${GREEN}Logs are available in:${NC}"
echo -e "API log:       ${BLUE}$SCRIPT_DIR/logs/api.log${NC}"
echo -e "Streamlit log: ${BLUE}$SCRIPT_DIR/logs/streamlit.log${NC}"
echo -e "\n${GREEN}Press Ctrl+C to stop all services${NC}"

# Wait for user interrupt
wait 