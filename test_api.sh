#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}1. Testing if the API is running...${NC}"
curl http://localhost:8000/

echo -e "\n${GREEN}2. Getting current collection stats...${NC}"
curl http://localhost:8000/stats

echo -e "\n${GREEN}3. Testing document upload (sample.txt)...${NC}"
# First create a sample text file
echo "This is a sample document about artificial intelligence and machine learning. 
RAG systems are becoming increasingly popular for building intelligent applications.
They combine the power of large language models with local document retrieval." > sample.txt

curl -X POST \
  http://localhost:8000/upload \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.txt"

echo -e "\n${GREEN}4. Testing RAG query...${NC}"
curl -X POST \
  http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are RAG systems?",
    "top_k": 3
  }'

echo -e "\n${GREEN}5. Getting updated collection stats...${NC}"
curl http://localhost:8000/stats

# Clean up
rm sample.txt

echo -e "\n${BLUE}Test script completed!${NC}" 