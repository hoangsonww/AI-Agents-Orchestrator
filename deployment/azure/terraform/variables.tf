# Azure Infrastructure Variables

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "location" {
  description = "Primary Azure region"
  type        = string
  default     = "eastus"
}

variable "location_secondary" {
  description = "Secondary Azure region for disaster recovery"
  type        = string
  default     = "westus2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ai-orchestrator"
}

# AKS Configuration
variable "aks_kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
  default     = "1.28"
}

variable "aks_node_count" {
  description = "Initial number of nodes in the default node pool"
  type        = number
  default     = 3
}

variable "aks_min_count" {
  description = "Minimum number of nodes for autoscaling"
  type        = number
  default     = 3
}

variable "aks_max_count" {
  description = "Maximum number of nodes for autoscaling"
  type        = number
  default     = 20
}

variable "aks_node_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "aks_os_disk_size_gb" {
  description = "OS disk size in GB for AKS nodes"
  type        = number
  default     = 128
}

# ACR Configuration
variable "acr_sku" {
  description = "Azure Container Registry SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Premium"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.acr_sku)
    error_message = "ACR SKU must be Basic, Standard, or Premium."
  }
}

variable "acr_admin_enabled" {
  description = "Enable ACR admin user"
  type        = bool
  default     = false
}

variable "acr_georeplication_enabled" {
  description = "Enable geo-replication for ACR"
  type        = bool
  default     = true
}

# Redis Configuration
variable "redis_capacity" {
  description = "Redis cache capacity (1, 2, 3, 4 for Premium)"
  type        = number
  default     = 1

  validation {
    condition     = contains([1, 2, 3, 4], var.redis_capacity)
    error_message = "Redis capacity must be 1, 2, 3, or 4."
  }
}

variable "redis_family" {
  description = "Redis cache family (P for Premium)"
  type        = string
  default     = "P"
}

variable "redis_sku_name" {
  description = "Redis cache SKU name"
  type        = string
  default     = "Premium"
}

# Storage Configuration
variable "storage_account_tier" {
  description = "Storage account tier (Standard, Premium)"
  type        = string
  default     = "Premium"
}

variable "storage_account_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
}

variable "workspace_share_quota" {
  description = "Workspace file share quota in GB"
  type        = number
  default     = 100
}

variable "sessions_share_quota" {
  description = "Sessions file share quota in GB"
  type        = number
  default     = 50
}

# Monitoring Configuration
variable "log_analytics_retention_days" {
  description = "Log Analytics workspace data retention in days"
  type        = number
  default     = 30
}

variable "enable_application_insights" {
  description = "Enable Application Insights"
  type        = bool
  default     = true
}

# Networking Configuration
variable "vnet_address_space" {
  description = "Virtual network address space"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "aks_subnet_prefix" {
  description = "AKS subnet address prefix"
  type        = list(string)
  default     = ["10.0.1.0/24"]
}

variable "appgw_subnet_prefix" {
  description = "Application Gateway subnet address prefix"
  type        = list(string)
  default     = ["10.0.2.0/24"]
}

variable "private_endpoints_subnet_prefix" {
  description = "Private endpoints subnet address prefix"
  type        = list(string)
  default     = ["10.0.3.0/24"]
}

variable "service_cidr" {
  description = "Kubernetes service CIDR"
  type        = string
  default     = "10.1.0.0/16"
}

variable "dns_service_ip" {
  description = "Kubernetes DNS service IP"
  type        = string
  default     = "10.1.0.10"
}

# Key Vault Configuration
variable "key_vault_sku_name" {
  description = "Key Vault SKU (standard, premium)"
  type        = string
  default     = "premium"
}

variable "key_vault_soft_delete_retention_days" {
  description = "Key Vault soft delete retention period in days"
  type        = number
  default     = 90
}

variable "key_vault_purge_protection_enabled" {
  description = "Enable Key Vault purge protection"
  type        = bool
  default     = true
}

# Application Gateway Configuration
variable "app_gateway_sku_name" {
  description = "Application Gateway SKU name"
  type        = string
  default     = "WAF_v2"
}

variable "app_gateway_sku_tier" {
  description = "Application Gateway SKU tier"
  type        = string
  default     = "WAF_v2"
}

variable "app_gateway_sku_capacity" {
  description = "Application Gateway SKU capacity"
  type        = number
  default     = 2
}

# Tags
variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Alerts Configuration
variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = "admin@example.com"
}

variable "alert_webhook_url" {
  description = "Webhook URL for alerts (e.g., Slack)"
  type        = string
  default     = ""
}

variable "cpu_alert_threshold" {
  description = "CPU usage threshold for alerts (percentage)"
  type        = number
  default     = 80
}

variable "memory_alert_threshold" {
  description = "Memory usage threshold for alerts (percentage)"
  type        = number
  default     = 85
}

# Feature Flags
variable "enable_azure_policy" {
  description = "Enable Azure Policy for AKS"
  type        = bool
  default     = true
}

variable "enable_private_cluster" {
  description = "Enable AKS private cluster"
  type        = bool
  default     = false
}

variable "enable_oms_agent" {
  description = "Enable OMS agent for container monitoring"
  type        = bool
  default     = true
}

variable "enable_defender" {
  description = "Enable Microsoft Defender for Containers"
  type        = bool
  default     = true
}
