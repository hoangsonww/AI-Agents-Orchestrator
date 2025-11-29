# Azure Production Infrastructure for AI Agents Orchestrator
# Terraform Configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.45"
    }
  }

  backend "azurerm" {
    resource_group_name  = "ai-orchestrator-tfstate-rg"
    storage_account_name = "aiorchestratortfstate"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "location_secondary" {
  description = "Secondary Azure region for DR"
  type        = string
  default     = "westus2"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "ai-orchestrator"
}

variable "aks_node_count" {
  description = "Initial AKS node count"
  type        = number
  default     = 3
}

variable "aks_min_count" {
  description = "Minimum AKS node count for autoscaling"
  type        = number
  default     = 3
}

variable "aks_max_count" {
  description = "Maximum AKS node count for autoscaling"
  type        = number
  default     = 20
}

variable "acr_sku" {
  description = "Azure Container Registry SKU"
  type        = string
  default     = "Premium"
}

# Locals
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    CostCenter  = "Engineering"
  }

  resource_prefix = "${var.project_name}-${var.environment}"
}

# Resource Group - Primary
resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

# Resource Group - Secondary (DR)
resource "azurerm_resource_group" "secondary" {
  name     = "${local.resource_prefix}-rg-dr"
  location = var.location_secondary
  tags     = merge(local.common_tags, { Purpose = "DisasterRecovery" })
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${local.resource_prefix}-vnet"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]

  tags = local.common_tags
}

# Subnets
resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.Sql"]
}

resource "azurerm_subnet" "app_gateway" {
  name                 = "appgw-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "private-endpoints-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  private_endpoint_network_policies_enabled = false
}

# Azure Container Registry
resource "azurerm_container_registry" "main" {
  name                = replace("${local.resource_prefix}acr", "-", "")
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.acr_sku
  admin_enabled       = false

  georeplications {
    location = var.location_secondary
    tags     = local.common_tags
  }

  network_rule_set {
    default_action = "Deny"

    ip_rule {
      action   = "Allow"
      ip_range = "0.0.0.0/0" # Replace with your IP ranges
    }
  }

  retention_policy {
    days    = 30
    enabled = true
  }

  trust_policy {
    enabled = true
  }

  tags = local.common_tags
}

# Azure Kubernetes Service (AKS)
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${local.resource_prefix}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${local.resource_prefix}-aks"
  kubernetes_version  = "1.28"

  default_node_pool {
    name                = "system"
    node_count          = var.aks_node_count
    vm_size             = "Standard_D4s_v3"
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count           = var.aks_min_count
    max_count           = var.aks_max_count
    os_disk_size_gb     = 128
    os_disk_type        = "Managed"

    upgrade_settings {
      max_surge = "33%"
    }

    tags = local.common_tags
  }

  # User node pool for applications
  # Defined separately below

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin     = "azure"
    network_policy     = "calico"
    load_balancer_sku  = "standard"
    outbound_type      = "loadBalancer"
    service_cidr       = "10.1.0.0/16"
    dns_service_ip     = "10.1.0.10"
  }

  auto_scaler_profile {
    balance_similar_node_groups      = true
    expander                         = "random"
    max_graceful_termination_sec     = 600
    scale_down_delay_after_add       = "10m"
    scale_down_unneeded              = "10m"
    scale_down_utilization_threshold = 0.5
  }

  azure_policy_enabled = true

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  tags = local.common_tags
}

# AKS User Node Pool
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_D4s_v3"
  node_count            = 3
  enable_auto_scaling   = true
  min_count             = 3
  max_count             = 20
  vnet_subnet_id        = azurerm_subnet.aks.id

  node_labels = {
    "workload" = "application"
  }

  tags = local.common_tags
}

# Role Assignment - ACR Pull
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.resource_prefix}-law"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${local.resource_prefix}-ai"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.common_tags
}

# Azure Key Vault
resource "azurerm_key_vault" "main" {
  name                       = "${replace(local.resource_prefix, "-", "")}kv"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "premium"
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"

    virtual_network_subnet_ids = [
      azurerm_subnet.aks.id,
      azurerm_subnet.private_endpoints.id
    ]
  }

  tags = local.common_tags
}

# Key Vault Access Policy for AKS
resource "azurerm_key_vault_access_policy" "aks" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].object_id

  secret_permissions = [
    "Get",
    "List"
  ]
}

# Azure Storage Account for Backups
resource "azurerm_storage_account" "backups" {
  name                     = "${replace(local.resource_prefix, "-", "")}backups"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS" # Geo-redundant

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }
  }

  tags = local.common_tags
}

# Azure Files for Persistent Storage
resource "azurerm_storage_account" "files" {
  name                     = "${replace(local.resource_prefix, "-", "")}files"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Premium"
  account_replication_type = "LRS"
  account_kind             = "FileStorage"

  tags = local.common_tags
}

resource "azurerm_storage_share" "workspace" {
  name                 = "workspace"
  storage_account_name = azurerm_storage_account.files.name
  quota                = 100
}

resource "azurerm_storage_share" "sessions" {
  name                 = "sessions"
  storage_account_name = azurerm_storage_account.files.name
  quota                = 50
}

# Azure Redis Cache
resource "azurerm_redis_cache" "main" {
  name                = "${local.resource_prefix}-redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 1
  family              = "P"
  sku_name            = "Premium"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_reserved = 50
    maxmemory_delta    = 50
    maxmemory_policy   = "allkeys-lru"
  }

  patch_schedule {
    day_of_week    = "Sunday"
    start_hour_utc = 2
  }

  tags = local.common_tags
}

# Azure Application Gateway (Layer 7 Load Balancer)
resource "azurerm_public_ip" "app_gateway" {
  name                = "${local.resource_prefix}-appgw-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]

  tags = local.common_tags
}

# Azure Front Door (Global Load Balancer)
resource "azurerm_cdn_frontdoor_profile" "main" {
  name                = "${local.resource_prefix}-afd"
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "Premium_AzureFrontDoor"

  tags = local.common_tags
}

# Azure Monitor Action Group
resource "azurerm_monitor_action_group" "main" {
  name                = "${local.resource_prefix}-action-group"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "aiorchest"

  email_receiver {
    name          = "sendtoadmin"
    email_address = "admin@example.com"
  }

  webhook_receiver {
    name        = "slack"
    service_uri = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  }

  tags = local.common_tags
}

# Azure Monitor Metric Alerts
resource "azurerm_monitor_metric_alert" "aks_cpu" {
  name                = "${local.resource_prefix}-aks-cpu-alert"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_kubernetes_cluster.main.id]
  description         = "Alert when AKS CPU usage is high"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_cpu_usage_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = local.common_tags
}

# Data Sources
data "azurerm_client_config" "current" {}

# Outputs
output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "aks_cluster_id" {
  value = azurerm_kubernetes_cluster.main.id
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "redis_hostname" {
  value     = azurerm_redis_cache.main.hostname
  sensitive = true
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.main.id
}

output "application_insights_instrumentation_key" {
  value     = azurerm_application_insights.main.instrumentation_key
  sensitive = true
}

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}
