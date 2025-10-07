#!/bin/bash
# Quick Deployment Script for Mandate Vault
# This script helps you deploy quickly with minimal configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main menu
show_menu() {
    print_header "Mandate Vault - Quick Deployment"
    echo "Choose your deployment option:"
    echo ""
    echo "1) Docker Compose (Local/Development) - ⭐ EASIEST"
    echo "2) Google Cloud Run (Production) - ⭐ RECOMMENDED"
    echo "3) Kubernetes (Enterprise)"
    echo "4) Check System Requirements"
    echo "5) Generate Secrets Only"
    echo "6) Exit"
    echo ""
    read -p "Enter your choice (1-6): " choice
    
    case $choice in
        1) deploy_docker_compose ;;
        2) deploy_cloud_run ;;
        3) deploy_kubernetes ;;
        4) check_requirements ;;
        5) generate_secrets ;;
        6) exit 0 ;;
        *) print_error "Invalid choice"; show_menu ;;
    esac
}

# Check system requirements
check_requirements() {
    print_header "System Requirements Check"
    
    local all_good=true
    
    # Check Docker
    if command_exists docker; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker installed: $DOCKER_VERSION"
    else
        print_error "Docker is not installed"
        all_good=false
    fi
    
    # Check Docker Compose
    if command_exists docker-compose; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose installed: $COMPOSE_VERSION"
    else
        print_warning "Docker Compose is not installed (optional for Docker Compose deployment)"
    fi
    
    # Check Python
    if command_exists python || command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 || python --version 2>&1)
        print_success "Python installed: $PYTHON_VERSION"
    else
        print_error "Python is not installed"
        all_good=false
    fi
    
    # Check gcloud
    if command_exists gcloud; then
        GCLOUD_VERSION=$(gcloud --version | head -n 1)
        print_success "gcloud CLI installed: $GCLOUD_VERSION"
    else
        print_warning "gcloud CLI is not installed (required for Cloud Run deployment)"
    fi
    
    # Check kubectl
    if command_exists kubectl; then
        KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null || echo "kubectl installed")
        print_success "kubectl installed: $KUBECTL_VERSION"
    else
        print_warning "kubectl is not installed (required for Kubernetes deployment)"
    fi
    
    # Check available memory
    if [[ "$OSTYPE" == "darwin"* ]]; then
        TOTAL_MEM=$(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}')
        print_info "Total memory: $TOTAL_MEM"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        TOTAL_MEM=$(free -h | grep Mem | awk '{print $2}')
        print_info "Total memory: $TOTAL_MEM"
    fi
    
    echo ""
    if [ "$all_good" = true ]; then
        print_success "All required dependencies are installed!"
    else
        print_error "Some required dependencies are missing. Please install them first."
    fi
    
    echo ""
    read -p "Press Enter to return to menu..."
    show_menu
}

# Generate secrets
generate_secrets() {
    print_header "Generate Secrets"
    
    print_info "Generating SECRET_KEY..."
    SECRET_KEY=$(python3 scripts/generate_secret_key.py 2>/dev/null || python -c "import secrets; print(secrets.token_urlsafe(32))")
    print_success "SECRET_KEY generated"
    
    print_info "Generating ACP_WEBHOOK_SECRET..."
    ACP_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || python -c "import secrets; print(secrets.token_urlsafe(32))")
    print_success "ACP_WEBHOOK_SECRET generated"
    
    print_info "Generating DB_PASSWORD..."
    DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || python -c "import secrets; print(secrets.token_urlsafe(24))")
    print_success "DB_PASSWORD generated"
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "Save these secrets securely! You'll need them for deployment."
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "SECRET_KEY=$SECRET_KEY"
    echo "ACP_WEBHOOK_SECRET=$ACP_SECRET"
    echo "DB_PASSWORD=$DB_PASSWORD"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    
    read -p "Write these to .env file? (y/n): " write_env
    if [[ "$write_env" == "y" || "$write_env" == "Y" ]]; then
        cat > .env << EOF
# Mandate Vault Environment Configuration
# Generated on $(date)

# Security (REQUIRED)
SECRET_KEY=$SECRET_KEY
ACP_WEBHOOK_SECRET=$ACP_SECRET

# Database
DB_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql+asyncpg://mandate_user:$DB_PASSWORD@db:5432/mandate_vault

# Application
ENVIRONMENT=production
DEBUG=false

# CORS (update with your frontend domain)
CORS_ORIGINS=http://localhost:3000

# Optional integrations
# SENTRY_DSN=
# GCS_BUCKET=
# KMS_KEY_ID=
EOF
        print_success ".env file created!"
        print_warning "Remember to update CORS_ORIGINS with your actual domain"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..."
    show_menu
}

# Deploy with Docker Compose
deploy_docker_compose() {
    print_header "Docker Compose Deployment"
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        read -p "Press Enter to return to menu..."
        show_menu
        return
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed."
        echo "Visit: https://docs.docker.com/compose/install/"
        read -p "Press Enter to return to menu..."
        show_menu
        return
    fi
    
    # Check for .env file
    if [ ! -f .env ]; then
        print_warning ".env file not found. Let's create one!"
        generate_secrets
        return
    fi
    
    print_info "Starting deployment..."
    
    # Build and start services
    print_info "Building Docker images..."
    docker-compose build
    
    print_info "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Services are running!"
    else
        print_error "Some services failed to start"
        docker-compose ps
        read -p "Press Enter to return to menu..."
        show_menu
        return
    fi
    
    # Run database migrations
    print_info "Running database migrations..."
    docker-compose exec -T api alembic upgrade head
    
    print_success "Database migrations completed!"
    
    # Seed initial data
    read -p "Create initial admin user? (y/n): " seed_data
    if [[ "$seed_data" == "y" || "$seed_data" == "Y" ]]; then
        print_info "Creating initial admin user..."
        docker-compose exec -T api python scripts/seed_initial_data.py
        print_success "Admin user created!"
    fi
    
    # Show deployment info
    print_header "Deployment Complete! 🎉"
    echo ""
    print_success "Mandate Vault is now running!"
    echo ""
    echo "📍 Service URLs:"
    echo "   API:        http://localhost:8000"
    echo "   API Docs:   http://localhost:8000/docs"
    echo "   Health:     http://localhost:8000/healthz"
    echo "   Grafana:    http://localhost:3001 (admin/admin)"
    echo "   Prometheus: http://localhost:9090"
    echo ""
    echo "🔧 Useful Commands:"
    echo "   View logs:     docker-compose logs -f api"
    echo "   Stop services: docker-compose down"
    echo "   Restart:       docker-compose restart api"
    echo ""
    
    read -p "Run smoke tests? (y/n): " run_tests
    if [[ "$run_tests" == "y" || "$run_tests" == "Y" ]]; then
        print_info "Running smoke tests..."
        
        # Wait a bit for the service to be fully ready
        sleep 5
        
        export TEST_EMAIL='admin@example.com'
        export TEST_PASSWORD='Admin123!@#'
        
        python3 scripts/smoke_authorizations.py || print_warning "Some smoke tests failed. Check the logs."
    fi
    
    echo ""
    read -p "Press Enter to return to menu..."
    show_menu
}

# Deploy to Google Cloud Run
deploy_cloud_run() {
    print_header "Google Cloud Run Deployment"
    
    # Check gcloud
    if ! command_exists gcloud; then
        print_error "gcloud CLI is not installed."
        echo "Visit: https://cloud.google.com/sdk/docs/install"
        read -p "Press Enter to return to menu..."
        show_menu
        return
    fi
    
    # Get project ID
    read -p "Enter your GCP Project ID: " PROJECT_ID
    
    if [ -z "$PROJECT_ID" ]; then
        print_error "Project ID cannot be empty"
        read -p "Press Enter to return to menu..."
        show_menu
        return
    fi
    
    print_info "Setting project to $PROJECT_ID..."
    gcloud config set project $PROJECT_ID
    
    # Enable APIs
    print_info "Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        sqladmin.googleapis.com \
        storage.googleapis.com \
        secretmanager.googleapis.com \
        artifactregistry.googleapis.com \
        2>/dev/null || print_warning "Some APIs might already be enabled"
    
    print_success "APIs enabled!"
    
    # Generate secrets if needed
    print_info "Setting up secrets..."
    
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    ACP_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    
    # Create secrets in Secret Manager
    echo -n "$SECRET_KEY" | gcloud secrets create mandate-vault-secret-key --data-file=- 2>/dev/null || \
        echo -n "$SECRET_KEY" | gcloud secrets versions add mandate-vault-secret-key --data-file=-
    
    echo -n "$ACP_SECRET" | gcloud secrets create mandate-vault-acp-webhook-secret --data-file=- 2>/dev/null || \
        echo -n "$ACP_SECRET" | gcloud secrets versions add mandate-vault-acp-webhook-secret --data-file=-
    
    echo -n "$DB_PASSWORD" | gcloud secrets create mandate-vault-db-password --data-file=- 2>/dev/null || \
        echo -n "$DB_PASSWORD" | gcloud secrets versions add mandate-vault-db-password --data-file=-
    
    print_success "Secrets created in Secret Manager!"
    
    # Ask about Cloud SQL
    read -p "Create Cloud SQL instance? (y/n): " create_sql
    if [[ "$create_sql" == "y" || "$create_sql" == "Y" ]]; then
        print_info "Creating Cloud SQL instance (this may take a few minutes)..."
        
        gcloud sql instances create mandate-vault-db \
            --database-version=POSTGRES_14 \
            --tier=db-f1-micro \
            --region=us-central1 \
            2>/dev/null || print_warning "Instance might already exist"
        
        gcloud sql databases create mandate_vault \
            --instance=mandate-vault-db \
            2>/dev/null || print_warning "Database might already exist"
        
        gcloud sql users create mandate_user \
            --instance=mandate-vault-db \
            --password=$DB_PASSWORD \
            2>/dev/null || print_warning "User might already exist"
        
        print_success "Cloud SQL instance created!"
    fi
    
    # Build and deploy
    print_info "Building container image..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/mandate-vault
    
    print_info "Deploying to Cloud Run..."
    gcloud run deploy mandate-vault \
        --image gcr.io/$PROJECT_ID/mandate-vault \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --min-instances 1 \
        --max-instances 10 \
        --set-env-vars ENVIRONMENT=production,DEBUG=false \
        --set-secrets SECRET_KEY=mandate-vault-secret-key:latest,ACP_WEBHOOK_SECRET=mandate-vault-acp-webhook-secret:latest
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe mandate-vault \
        --region us-central1 \
        --format 'value(status.url)')
    
    print_header "Deployment Complete! 🎉"
    echo ""
    print_success "Mandate Vault is deployed to Cloud Run!"
    echo ""
    echo "📍 Service URL: $SERVICE_URL"
    echo "📍 API Docs:    $SERVICE_URL/docs"
    echo "📍 Health:      $SERVICE_URL/healthz"
    echo ""
    
    echo ""
    read -p "Press Enter to return to menu..."
    show_menu
}

# Deploy to Kubernetes
deploy_kubernetes() {
    print_header "Kubernetes Deployment"
    
    # Check kubectl
    if ! command_exists kubectl; then
        print_error "kubectl is not installed."
        echo "Visit: https://kubernetes.io/docs/tasks/tools/"
        read -p "Press Enter to return to menu..."
        show_menu
        return
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &>/dev/null; then
        print_error "Not connected to a Kubernetes cluster."
        print_info "Please configure kubectl to connect to your cluster first."
        read -p "Press Enter to return to menu..."
        show_menu
        return
    fi
    
    print_success "Connected to Kubernetes cluster"
    
    # Generate secrets
    print_info "Generating secrets..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    ACP_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    read -p "Enter DATABASE_URL: " DATABASE_URL
    
    # Create namespace
    print_info "Creating namespace..."
    kubectl apply -f k8s/namespace.yaml
    
    # Create secrets
    print_info "Creating secrets..."
    kubectl create secret generic mandate-vault-secrets \
        --namespace=mandate-vault \
        --from-literal=SECRET_KEY=$SECRET_KEY \
        --from-literal=ACP_WEBHOOK_SECRET=$ACP_SECRET \
        --from-literal=DATABASE_URL=$DATABASE_URL \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy application
    print_info "Deploying application..."
    kubectl apply -f k8s/
    
    # Wait for deployment
    print_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s \
        deployment/mandate-vault -n mandate-vault
    
    print_header "Deployment Complete! 🎉"
    echo ""
    print_success "Mandate Vault is deployed to Kubernetes!"
    echo ""
    echo "🔧 Useful Commands:"
    echo "   View pods:     kubectl get pods -n mandate-vault"
    echo "   View logs:     kubectl logs -f deployment/mandate-vault -n mandate-vault"
    echo "   Port forward:  kubectl port-forward svc/mandate-vault 8000:8000 -n mandate-vault"
    echo ""
    
    read -p "Port forward to localhost:8000? (y/n): " port_forward
    if [[ "$port_forward" == "y" || "$port_forward" == "Y" ]]; then
        print_info "Port forwarding... (press Ctrl+C to stop)"
        kubectl port-forward svc/mandate-vault 8000:8000 -n mandate-vault
    fi
    
    echo ""
    read -p "Press Enter to return to menu..."
    show_menu
}

# Main execution
clear
show_menu
