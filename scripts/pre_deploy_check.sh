#!/bin/bash
# Pre-Deployment Validation Script
# Checks if system is ready for deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Mandate Vault - Pre-Deployment Check              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"

ERRORS=0
WARNINGS=0

# Function to check command
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✅ $1 is installed${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 is NOT installed${NC}"
        ((ERRORS++))
        return 1
    fi
}

# Function to check file
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $1 exists${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $1 not found${NC}"
        ((WARNINGS++))
        return 1
    fi
}

# Check Docker
echo -e "\n${BLUE}Checking Docker...${NC}"
if check_command docker; then
    DOCKER_VERSION=$(docker --version)
    echo -e "   Version: $DOCKER_VERSION"
    
    # Check if Docker daemon is running
    if docker ps &> /dev/null; then
        echo -e "${GREEN}   ✅ Docker daemon is running${NC}"
    else
        echo -e "${RED}   ❌ Docker daemon is NOT running${NC}"
        echo -e "${YELLOW}   → Start Docker Desktop or run: sudo systemctl start docker${NC}"
        ((ERRORS++))
    fi
fi

# Check Docker Compose
echo -e "\n${BLUE}Checking Docker Compose...${NC}"
if check_command docker-compose; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo -e "   Version: $COMPOSE_VERSION"
elif check_command "docker compose"; then
    echo -e "${GREEN}✅ docker compose (v2) is installed${NC}"
else
    echo -e "${RED}❌ Neither docker-compose nor 'docker compose' found${NC}"
    ((ERRORS++))
fi

# Check Python
echo -e "\n${BLUE}Checking Python...${NC}"
if check_command python3; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "   Version: $PYTHON_VERSION"
elif check_command python; then
    PYTHON_VERSION=$(python --version)
    echo -e "   Version: $PYTHON_VERSION"
fi

# Check required files
echo -e "\n${BLUE}Checking required files...${NC}"
check_file "docker-compose.yml"
check_file "Dockerfile"
check_file "requirements.txt"
check_file "alembic.ini"

# Check for .env file
echo -e "\n${BLUE}Checking environment configuration...${NC}"
if check_file ".env"; then
    # Check for required variables
    if grep -q "SECRET_KEY=CHANGE-THIS" .env 2>/dev/null; then
        echo -e "${RED}   ❌ SECRET_KEY not configured (still has default value)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}   ✅ SECRET_KEY is configured${NC}"
    fi
    
    if grep -q "DATABASE_URL" .env 2>/dev/null; then
        echo -e "${GREEN}   ✅ DATABASE_URL is configured${NC}"
    else
        echo -e "${YELLOW}   ⚠️  DATABASE_URL not found${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}   ⚠️  No .env file found${NC}"
    echo -e "${YELLOW}   → Copy env.example to .env and configure it${NC}"
    ((WARNINGS++))
fi

# Check disk space
echo -e "\n${BLUE}Checking disk space...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    AVAILABLE=$(df -H / | awk 'NR==2 {print $4}')
    echo -e "   Available: $AVAILABLE"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    AVAILABLE=$(df -h / | awk 'NR==2 {print $4}')
    echo -e "   Available: $AVAILABLE"
fi

# Check available memory
echo -e "\n${BLUE}Checking available memory...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    TOTAL_MEM=$(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}')
    echo -e "   Total: $TOTAL_MEM"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TOTAL_MEM=$(free -h | grep Mem | awk '{print $2}')
    echo -e "   Total: $TOTAL_MEM"
fi

# Check ports
echo -e "\n${BLUE}Checking required ports...${NC}"
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an 2>/dev/null | grep -q ":$1.*LISTEN"; then
        echo -e "${YELLOW}   ⚠️  Port $1 is already in use${NC}"
        ((WARNINGS++))
        return 1
    else
        echo -e "${GREEN}   ✅ Port $1 is available${NC}"
        return 0
    fi
}

check_port 8000  # API
check_port 5432  # PostgreSQL
check_port 6379  # Redis
check_port 3001  # Grafana
check_port 9090  # Prometheus

# Check network connectivity
echo -e "\n${BLUE}Checking network connectivity...${NC}"
if ping -c 1 google.com &> /dev/null || ping -c 1 8.8.8.8 &> /dev/null; then
    echo -e "${GREEN}✅ Internet connection is available${NC}"
else
    echo -e "${YELLOW}⚠️  No internet connection${NC}"
    echo -e "${YELLOW}   Some features may not work (image pulls, external APIs)${NC}"
    ((WARNINGS++))
fi

# Summary
echo -e "\n${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Summary                                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}\n"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! You're ready to deploy!${NC}\n"
    echo -e "Next steps:"
    echo -e "  1. Run: ${BLUE}docker-compose up -d${NC}"
    echo -e "  2. Or:  ${BLUE}./scripts/quick_deploy.sh${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Found $WARNINGS warning(s)${NC}"
    echo -e "You can proceed with deployment, but review the warnings above.\n"
    echo -e "Ready to deploy? Run: ${BLUE}docker-compose up -d${NC}"
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo -e "Please fix the errors above before deploying.\n"
    
    echo -e "${BLUE}Common fixes:${NC}"
    echo -e "  • Install Docker: https://docs.docker.com/get-docker/"
    echo -e "  • Start Docker: Open Docker Desktop or run 'sudo systemctl start docker'"
    echo -e "  • Configure .env: Copy env.example to .env and update values"
    echo -e "  • Generate secrets: python3 scripts/generate_secret_key.py"
    exit 1
fi
