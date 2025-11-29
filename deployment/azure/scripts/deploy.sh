#!/bin/bash
set -euo pipefail

# Azure Deployment Script for AI Agents Orchestrator
# This script automates the complete Azure infrastructure deployment

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ai-orchestrator"
ENVIRONMENT="${ENVIRONMENT:-production}"
LOCATION="${LOCATION:-eastus}"
RESOURCE_GROUP="${PROJECT_NAME}-${ENVIRONMENT}-rg"
AKS_CLUSTER="${PROJECT_NAME}-${ENVIRONMENT}-aks"
ACR_NAME="${PROJECT_NAME}${ENVIRONMENT}acr"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not found. Install: https://docs.microsoft.com/cli/azure/install-azure-cli"
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform not found. Install: https://www.terraform.io/downloads"
        exit 1
    fi

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Install: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi

    # Check Helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm not found. Install: https://helm.sh/docs/intro/install/"
        exit 1
    fi

    log_success "All prerequisites satisfied"
}

azure_login() {
    log_info "Checking Azure login status..."

    if ! az account show &> /dev/null; then
        log_warning "Not logged into Azure. Initiating login..."
        az login
    else
        log_success "Already logged into Azure"
        az account show --query "{Name:name, SubscriptionId:id, TenantId:tenantId}" -o table
    fi
}

create_terraform_backend() {
    log_info "Creating Terraform remote backend..."

    local backend_rg="${PROJECT_NAME}-tfstate-rg"
    local backend_storage="${PROJECT_NAME}tfstate"

    # Create resource group if it doesn't exist
    if ! az group show --name "$backend_rg" &> /dev/null; then
        az group create --name "$backend_rg" --location "$LOCATION"
        log_success "Created resource group: $backend_rg"
    fi

    # Create storage account if it doesn't exist
    if ! az storage account show --name "$backend_storage" --resource-group "$backend_rg" &> /dev/null; then
        az storage account create \
            --name "$backend_storage" \
            --resource-group "$backend_rg" \
            --location "$LOCATION" \
            --sku Standard_LRS \
            --encryption-services blob \
            --https-only true \
            --min-tls-version TLS1_2
        log_success "Created storage account: $backend_storage"
    fi

    # Create container if it doesn't exist
    if ! az storage container show --name "tfstate" --account-name "$backend_storage" &> /dev/null; then
        az storage container create \
            --name "tfstate" \
            --account-name "$backend_storage" \
            --auth-mode login
        log_success "Created storage container: tfstate"
    fi
}

deploy_terraform() {
    log_info "Deploying Terraform infrastructure..."

    cd "$(dirname "$0")/../terraform"

    # Initialize Terraform
    terraform init

    # Plan deployment
    terraform plan \
        -var="environment=$ENVIRONMENT" \
        -var="location=$LOCATION" \
        -out=tfplan

    # Ask for confirmation
    read -p "Apply Terraform plan? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_warning "Terraform deployment cancelled"
        return
    fi

    # Apply deployment
    terraform apply tfplan

    log_success "Terraform infrastructure deployed"

    # Save outputs
    terraform output -json > ../outputs.json
}

configure_kubectl() {
    log_info "Configuring kubectl for AKS..."

    az aks get-credentials \
        --resource-group "$RESOURCE_GROUP" \
        --name "$AKS_CLUSTER" \
        --overwrite-existing

    log_success "kubectl configured"

    # Verify connection
    kubectl cluster-info
}

install_ingress_controller() {
    log_info "Installing NGINX Ingress Controller..."

    # Add Helm repo
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update

    # Install NGINX Ingress
    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --set controller.service.externalTrafficPolicy=Local \
        --set controller.metrics.enabled=true \
        --set controller.podAnnotations."prometheus\.io/scrape"=true \
        --set controller.podAnnotations."prometheus\.io/port"=10254

    log_success "NGINX Ingress Controller installed"
}

install_cert_manager() {
    log_info "Installing cert-manager for TLS..."

    # Add Helm repo
    helm repo add jetstack https://charts.jetstack.io
    helm repo update

    # Install cert-manager
    helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --set installCRDs=true \
        --set global.leaderElection.namespace=cert-manager

    log_success "cert-manager installed"

    # Wait for cert-manager to be ready
    kubectl wait --for=condition=available --timeout=300s \
        deployment/cert-manager -n cert-manager
    kubectl wait --for=condition=available --timeout=300s \
        deployment/cert-manager-webhook -n cert-manager
}

install_prometheus_stack() {
    log_info "Installing Prometheus monitoring stack..."

    # Add Helm repo
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update

    # Install kube-prometheus-stack
    helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set prometheus.prometheusSpec.retention=30d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --set grafana.enabled=true \
        --set grafana.adminPassword=admin123 \
        --set alertmanager.enabled=true

    log_success "Prometheus stack installed"
}

create_namespace() {
    log_info "Creating application namespace..."

    kubectl create namespace ai-orchestrator --dry-run=client -o yaml | kubectl apply -f -

    # Label namespace
    kubectl label namespace ai-orchestrator \
        environment="$ENVIRONMENT" \
        managed-by=terraform \
        --overwrite

    log_success "Namespace created"
}

configure_acr_integration() {
    log_info "Configuring ACR integration with AKS..."

    # Get ACR ID
    ACR_ID=$(az acr show --name "${ACR_NAME//-/}" --query id -o tsv)

    # Attach ACR to AKS
    az aks update \
        --resource-group "$RESOURCE_GROUP" \
        --name "$AKS_CLUSTER" \
        --attach-acr "$ACR_ID"

    log_success "ACR integrated with AKS"
}

apply_kubernetes_manifests() {
    log_info "Applying Kubernetes manifests..."

    cd "$(dirname "$0")/../../kubernetes"

    # Apply in order
    kubectl apply -f configmap.yaml -n ai-orchestrator
    kubectl apply -f pvc.yaml -n ai-orchestrator
    kubectl apply -f blue-green-deployment.yaml -n ai-orchestrator
    kubectl apply -f hpa.yaml -n ai-orchestrator
    kubectl apply -f ingress-nginx.yaml -n ai-orchestrator

    log_success "Kubernetes manifests applied"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Check nodes
    log_info "Cluster nodes:"
    kubectl get nodes

    # Check deployments
    log_info "Deployments:"
    kubectl get deployments -n ai-orchestrator

    # Check pods
    log_info "Pods:"
    kubectl get pods -n ai-orchestrator

    # Check services
    log_info "Services:"
    kubectl get services -n ai-orchestrator

    # Check ingress
    log_info "Ingress:"
    kubectl get ingress -n ai-orchestrator

    log_success "Deployment verification complete"
}

print_summary() {
    log_success "========================================="
    log_success "Azure Deployment Complete!"
    log_success "========================================="
    echo ""
    log_info "Resource Group: $RESOURCE_GROUP"
    log_info "AKS Cluster: $AKS_CLUSTER"
    log_info "ACR: ${ACR_NAME//-/}.azurecr.io"
    echo ""
    log_info "Next steps:"
    echo "  1. Build and push Docker image:"
    echo "     az acr build -t ai-orchestrator:latest -r ${ACR_NAME//-/} ."
    echo ""
    echo "  2. Access Grafana (port-forward):"
    echo "     kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80"
    echo "     Username: admin, Password: admin123"
    echo ""
    echo "  3. Get application endpoint:"
    echo "     kubectl get ingress -n ai-orchestrator"
    echo ""
    echo "  4. Monitor deployment:"
    echo "     kubectl get pods -n ai-orchestrator -w"
}

# Main execution
main() {
    log_info "Starting Azure deployment for $PROJECT_NAME ($ENVIRONMENT)"
    echo ""

    check_prerequisites
    azure_login
    create_terraform_backend
    deploy_terraform
    configure_kubectl
    create_namespace
    configure_acr_integration
    install_ingress_controller
    install_cert_manager
    install_prometheus_stack
    apply_kubernetes_manifests
    verify_deployment
    print_summary
}

# Run main function
main "$@"
