# Azure Deployment

Complete Azure infrastructure for AI Agents Orchestrator using Terraform.

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/hoangsonww/AI-Agents-Orchestrator.git
cd AI-Agents-Orchestrator/deployment/azure

# 2. Run deployment script
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## Infrastructure Components

### Compute & Orchestration
- **Azure Kubernetes Service (AKS)**: Managed Kubernetes cluster
  - Kubernetes 1.28
  - 2 node pools (system + user)
  - Auto-scaling (3-20 nodes)
  - Azure CNI networking
  - Calico network policies

### Container Registry
- **Azure Container Registry (ACR)**: Private Docker registry
  - Premium tier with geo-replication
  - Vulnerability scanning
  - Image signing
  - 30-day retention policy

### Load Balancing
- **Azure Application Gateway**: Layer 7 load balancer
  - WAF v2 with OWASP protection
  - SSL/TLS termination
  - Auto-scaling

- **Azure Front Door**: Global load balancer
  - CDN capabilities
  - DDoS protection
  - Bot protection

### Data & Caching
- **Azure Redis Cache**: Premium Redis
  - 6 GB capacity
  - Geo-replication
  - Data persistence
  - VNet integration

- **Azure Files**: Persistent storage
  - Premium SSD-backed
  - 100 GB workspace share
  - 50 GB sessions share

### Security
- **Azure Key Vault**: Secrets management
  - Premium tier (HSM-backed)
  - Certificate management
  - 90-day soft delete
  - Purge protection

### Monitoring
- **Azure Monitor**: Comprehensive monitoring
  - 30-day retention
  - Custom metrics
  - Alerting

- **Application Insights**: APM
  - Distributed tracing
  - Performance monitoring
  - Failure tracking

## Directory Structure

```
azure/
├── terraform/
│   ├── main.tf          # Main Terraform configuration
│   ├── variables.tf     # Input variables
│   └── outputs.json     # Terraform outputs
├── bicep/               # Alternative IaC (Bicep)
├── scripts/
│   └── deploy.sh        # Automated deployment script
└── README.md            # This file
```

## Prerequisites

### Tools
- Azure CLI 2.54.0+
- Terraform 1.5.0+
- kubectl 1.28+
- Helm 3.12+

### Azure Requirements
- Active Azure subscription
- Owner or Contributor role
- Resource quotas:
  - 64+ vCPU quota per region
  - 10+ public IPs per region

## Manual Deployment

### 1. Login to Azure

```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Review Plan

```bash
terraform plan \
  -var="environment=production" \
  -var="location=eastus" \
  -out=tfplan
```

### 4. Apply Infrastructure

```bash
terraform apply tfplan
```

### 5. Configure kubectl

```bash
az aks get-credentials \
  --resource-group ai-orchestrator-production-rg \
  --name ai-orchestrator-production-aks
```

### 6. Verify Deployment

```bash
kubectl cluster-info
kubectl get nodes
```

## Configuration

### Terraform Variables

Key variables in `variables.tf`:

```hcl
# Environment
environment = "production"  # production, staging, development

# Regions
location = "eastus"
location_secondary = "westus2"

# AKS
aks_node_count = 3
aks_min_count = 3
aks_max_count = 20
aks_node_vm_size = "Standard_D4s_v3"

# ACR
acr_sku = "Premium"
acr_georeplication_enabled = true

# Redis
redis_capacity = 1
redis_sku_name = "Premium"
```

### Custom Configuration

Create `terraform.tfvars`:

```hcl
environment = "production"
location = "eastus"
project_name = "ai-orchestrator"
aks_max_count = 30
alert_email = "your-email@example.com"
```

## Post-Deployment

### Install Core Components

```bash
# NGINX Ingress Controller
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# cert-manager
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Prometheus + Grafana
helm upgrade --install kube-prometheus-stack \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### Deploy Application

```bash
# Create namespace
kubectl create namespace ai-orchestrator

# Apply manifests
kubectl apply -f ../../kubernetes/ -n ai-orchestrator
```

### Build and Push Image

```bash
# Login to ACR
az acr login --name aiorchestrator productionacr

# Build and push
az acr build \
  --registry aiorchestrator productionacr \
  --image ai-orchestrator:latest \
  --image ai-orchestrator:$(git rev-parse --short HEAD) \
  .
```

## Outputs

Terraform outputs available via `terraform output`:

```bash
# AKS cluster name
terraform output aks_cluster_name

# ACR login server
terraform output acr_login_server

# Key Vault URI
terraform output key_vault_uri

# Redis hostname
terraform output redis_hostname

# Log Analytics workspace ID
terraform output log_analytics_workspace_id
```

## Monitoring

### Access Grafana

```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# Open http://localhost:3000
# Username: admin, Password: admin123
```

### View Azure Monitor

```bash
# Open in Azure Portal
az monitor metrics list \
  --resource $(az aks show -g ai-orchestrator-production-rg -n ai-orchestrator-production-aks --query id -o tsv) \
  --metric-names "node_cpu_usage_percentage"
```

## Cost Estimation

**Monthly Cost Breakdown:**

| Service | Configuration | Cost (USD) |
|---------|--------------|------------|
| AKS | 6x D4s_v3 nodes | ~$750 |
| ACR | Premium + geo-replication | ~$250 |
| App Gateway | WAF_v2 | ~$250 |
| Azure Front Door | Premium | ~$300 |
| Key Vault | Premium | ~$50 |
| Redis Cache | P1 (6 GB) | ~$300 |
| Azure Files | 150 GB Premium | ~$200 |
| Monitoring | 30-day retention | ~$150 |
| Bandwidth | Outbound | ~$100 |
| **Total** | | **~$2,350** |

Use Azure Pricing Calculator for precise estimates.

## Disaster Recovery

### Backup

```bash
# Install Velero for backups
helm upgrade --install velero vmware-tanzu/velero \
  --namespace velero \
  --create-namespace \
  --set configuration.provider=azure
```

### Multi-Region

Infrastructure is deployed in two regions:
- **Primary**: East US
- **Secondary**: West US 2 (DR)

ACR automatically replicates images to secondary region.

## Troubleshooting

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n ai-orchestrator
kubectl logs <pod-name> -n ai-orchestrator
```

**Image pull errors:**
```bash
# Verify ACR integration
az aks check-acr \
  --resource-group ai-orchestrator-production-rg \
  --name ai-orchestrator-production-aks \
  --acr aiorchestrator productionacr.azurecr.io
```

**Node scaling issues:**
```bash
# Check cluster autoscaler logs
kubectl logs -n kube-system deployment/cluster-autoscaler
```

### Get Support

```bash
# Create Azure support ticket
az support tickets create \
  --ticket-name "AKS-Issue-$(date +%Y%m%d)" \
  --title "AKS cluster issues" \
  --description "Description of issue" \
  --severity moderate
```

## Cleanup

### Destroy Infrastructure

```bash
# CAUTION: This will delete all resources
cd terraform
terraform destroy \
  -var="environment=production" \
  -var="location=eastus"
```

### Delete Specific Resources

```bash
# Delete resource group
az group delete \
  --name ai-orchestrator-production-rg \
  --yes \
  --no-wait
```

## Security Best Practices

1. **Enable private cluster** (if required):
   ```hcl
   enable_private_cluster = true
   ```

2. **Use managed identities** (already configured):
   - System-assigned identity for AKS
   - Key Vault integration via managed identity

3. **Enable network policies** (already configured):
   - Calico network policies
   - Pod security policies

4. **Regular updates**:
   ```bash
   # Update AKS
   az aks upgrade \
     --resource-group ai-orchestrator-production-rg \
     --name ai-orchestrator-production-aks \
     --kubernetes-version 1.29
   ```

## Additional Resources

- [Complete Deployment Guide](../../DEPLOYMENT.md)
- [Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Architecture Documentation](../../ARCHITECTURE.md)

## Support

For issues:
1. Check logs: `kubectl logs -n ai-orchestrator -l app=ai-orchestrator`
2. Review Azure Monitor dashboards
3. Check Application Insights
4. Open GitHub issue

---

**Maintained By**: DevOps Team
**Last Updated**: 2024-01-15
**Version**: 1.0.0
