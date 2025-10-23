#!/bin/bash

# FireBoard Integration - Quick Start Development Script

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}FireBoard Development Environment${NC}"
echo -e "${BLUE}=====================================${NC}\n"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠  Docker is not installed${NC}"
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${YELLOW}⚠  Docker is not running${NC}"
    echo "Please start Docker Desktop"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}\n"

# Start containers
echo -e "${BLUE}Starting Home Assistant...${NC}"
docker-compose up -d

echo ""
echo -e "${GREEN}✓ Home Assistant is starting!${NC}\n"

echo -e "${BLUE}Access Home Assistant at:${NC} http://localhost:8123"
echo ""
echo -e "${YELLOW}First startup takes 2-3 minutes while initializing...${NC}"
echo ""
echo "Commands:"
echo "  • View logs:    docker-compose logs -f homeassistant"
echo "  • Restart:      docker-compose restart homeassistant"
echo "  • Stop:         docker-compose down"
echo "  • Shell access: docker exec -it ha-fireboard-dev /bin/bash"
echo ""
echo -e "${BLUE}Opening logs in 5 seconds...${NC}"
sleep 5

docker-compose logs -f homeassistant

