#!/bin/bash
# 🚀 Mandate Vault - Free Deployment Commands
# Run these commands to deploy to production (100% FREE)

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🚀 Mandate Vault - FREE Production Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 1: Ensure we're in the right directory
cd /Users/alexlim/Desktop/mandate_vault

echo -e "${GREEN}✅ Step 1: Repository Check${NC}"
echo "Current directory: $(pwd)"
echo ""

# Step 2: Initialize git if needed
if [ ! -d .git ]; then
    echo -e "${YELLOW}Initializing Git repository...${NC}"
    git init
    echo -e "${GREEN}✅ Git initialized${NC}"
else
    echo -e "${GREEN}✅ Git already initialized${NC}"
fi
echo ""

# Step 3: Add all files
echo -e "${YELLOW}Adding files to git...${NC}"
git add .
echo -e "${GREEN}✅ Files added${NC}"
echo ""

# Step 4: Commit
echo -e "${YELLOW}Creating commit...${NC}"
git commit -m "Deploy: Enterprise API with multi-protocol support (AP2 + ACP)" || echo "Already committed"
echo -e "${GREEN}✅ Commit created${NC}"
echo ""

# Step 5: Check for GitHub remote
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  ACTION REQUIRED: Create GitHub Repository${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "1. Go to: https://github.com/new"
echo "2. Repository name: mandate-vault"
echo "3. Make it PUBLIC (required for free Render deployment)"
echo "4. Don't initialize with README"
echo "5. Click 'Create repository'"
echo ""
read -p "Press Enter once you've created the GitHub repository..."
echo ""

# Step 6: Get GitHub username
echo -e "${YELLOW}What's your GitHub username?${NC}"
read -p "GitHub username: " GITHUB_USERNAME
echo ""

# Step 7: Set branch to main
echo -e "${YELLOW}Setting branch to main...${NC}"
git branch -M main
echo -e "${GREEN}✅ Branch set to main${NC}"
echo ""

# Step 8: Add remote (remove if exists)
echo -e "${YELLOW}Adding GitHub remote...${NC}"
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$GITHUB_USERNAME/mandate-vault.git"
echo -e "${GREEN}✅ Remote added${NC}"
echo ""

# Step 9: Push to GitHub
echo -e "${YELLOW}Pushing to GitHub...${NC}"
git push -u origin main --force
echo -e "${GREEN}✅ Code pushed to GitHub!${NC}"
echo ""

# Step 10: Display deployment instructions
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 GitHub Repository Created!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Repository URL: https://github.com/$GITHUB_USERNAME/mandate-vault"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📋 NEXT STEPS - Deploy to Render.com (FREE)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "1. Go to: https://render.com"
echo "2. Sign up with GitHub (FREE, no credit card)"
echo ""
echo "3. Create PostgreSQL Database:"
echo "   • Click 'New +' → PostgreSQL"
echo "   • Name: mandate-vault-db"
echo "   • Region: Oregon (US West)"
echo "   • Plan: FREE"
echo "   • Copy the 'Internal Database URL'"
echo ""
echo "4. Create Web Service:"
echo "   • Click 'New +' → Web Service"
echo "   • Connect your mandate-vault repository"
echo "   • Runtime: Docker"
echo "   • Plan: FREE"
echo ""
echo "5. Add Environment Variables:"
echo "   SECRET_KEY=aA-PqbQIpyvdOwfhUfzV-nuwioXVf-KQOxbMfSGTRBY"
echo "   ACP_WEBHOOK_SECRET=jFqzEkz6LRFFmD-vwwxHyFaWzE0jjjpkSUZUM37dCxA"
echo "   DATABASE_URL=[paste Internal Database URL]"
echo "   ENVIRONMENT=production"
echo "   DEBUG=false"
echo "   ACP_ENABLE=true"
echo "   CORS_ORIGINS=*"
echo ""
echo "6. Click 'Create Web Service'"
echo ""
echo "7. Once deployed, run in Shell tab:"
echo "   alembic upgrade head"
echo "   python scripts/seed_initial_data.py"
echo ""
echo -e "${GREEN}📖 Full Instructions: DEPLOY_FREE_NOW.md${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🌐 Deploy Landing Page to Vercel (FREE)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "1. Go to: https://vercel.com"
echo "2. Sign up with GitHub (FREE)"
echo "3. Import your mandate-vault repository"
echo "4. Deploy!"
echo ""
echo -e "${GREEN}🎉 Your production deployment will be ready in 10 minutes!${NC}"
echo ""

