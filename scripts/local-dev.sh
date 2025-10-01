#!/bin/bash
# Local Development Setup Script
# ===============================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Setting up local development environment...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp config/env.development.template .env
    
    # Generate SECRET_KEY
    SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
    sed -i.bak "s|your-secret-key|${SECRET_KEY}|g" .env
    rm .env.bak
    
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${YELLOW}.env file already exists${NC}"
fi

# Start Docker Compose
echo -e "${GREEN}Starting Docker Compose...${NC}"
docker-compose up -d

# Wait for database
echo -e "${YELLOW}Waiting for database...${NC}"
sleep 5

# Run migrations
echo -e "${GREEN}Running database migrations...${NC}"
docker-compose exec -T api alembic upgrade head

# Seed data (optional)
read -p "Seed test data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Seeding test data...${NC}"
    docker-compose exec -T api python seed_initial_data.py
fi

# Show status
echo -e "${GREEN}✓ Setup complete!${NC}"
echo -e "${GREEN}Services:${NC}"
echo -e "  API: http://localhost:8000"
echo -e "  Docs: http://localhost:8000/docs"
echo -e "  Prometheus: http://localhost:9090"
echo -e "  Grafana: http://localhost:3001"
echo -e ""
echo -e "View logs: ${YELLOW}docker-compose logs -f api${NC}"
echo -e "Stop: ${YELLOW}docker-compose down${NC}"

