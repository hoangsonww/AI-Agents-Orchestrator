# Production Deployment Guide

This guide covers all production deployment strategies for the AI Agents Orchestrator.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Deployment Strategies](#deployment-strategies)
  - [Blue-Green Deployment](#blue-green-deployment)
  - [Canary Deployment](#canary-deployment)
  - [Rolling Update](#rolling-update)
- [Load Balancing](#load-balancing)
- [Auto-Scaling](#auto-scaling)
- [Monitoring & Alerting](#monitoring--alerting)
- [Disaster Recovery](#disaster-recovery)
- [Troubleshooting](#troubleshooting)

## Overview

The AI Agents Orchestrator supports multiple production-ready deployment strategies:

- **Blue-Green**: Zero-downtime deployment with instant rollback capability
- **Canary**: Gradual rollout with progressive traffic shifting (10% → 25% → 50% → 100%)
- **Rolling Update**: Kubernetes-native rolling updates with configurable parameters

## Prerequisites

### Required Tools

```bash
# Kubernetes
kubectl version >= 1.24

# Docker
docker version >= 20.10

# Helm (optional)
helm version >= 3.10

# Jenkins (for CI/CD)
jenkins >= 2.400
```

### Kubernetes Cluster Setup

```bash
# Create namespace
kubectl create namespace ai-orchestrator

# Create secrets
kubectl create secret generic ai-orchestrator-secrets \
  --from-literal=SECRET_KEY='your-secret-key' \
  --namespace=ai-orchestrator

# Apply base configurations
kubectl apply -f deployment/kubernetes/configmap.yaml
kubectl apply -f deployment/kubernetes/pvc.yaml
```

## Deployment Strategies

### Blue-Green Deployment

Blue-Green deployment provides zero-downtime deployments with instant rollback capability.

#### Architecture

```
                    Load Balancer
                         |
                    Service (selector: version)
                    /              \
              Blue (v1.0)        Green (v1.1)
              3 replicas         3 replicas
              [Active]           [Standby]
```

#### Deployment Process

1. **Deploy to Green environment**:
```bash
# Update green deployment with new image
kubectl set image deployment/ai-orchestrator-green \
  ai-orchestrator=ai-orchestrator:v1.1 \
  -n ai-orchestrator

# Scale up green
kubectl scale deployment/ai-orchestrator-green --replicas=3 -n ai-orchestrator
```

2. **Verify Green environment**:
```bash
# Run smoke tests
python scripts/smoke_tests.py --environment green

# Check health
kubectl exec -n ai-orchestrator \
  $(kubectl get pod -n ai-orchestrator -l version=green -o name | head -1) \
  -- curl -f http://localhost:5001/health
```

3. **Switch traffic** (using automation script):
```bash
# Automated switch with health checks
./deployment/scripts/blue-green-switch.sh blue green
```

Or manually:
```bash
# Patch service to point to green
kubectl patch service ai-orchestrator-service -n ai-orchestrator \
  -p '{"spec":{"selector":{"version":"green"}}}'
```

4. **Monitor and verify**:
```bash
# Watch metrics in Grafana
# Check logs
kubectl logs -n ai-orchestrator -l version=green --tail=100 -f

# If issues detected, instant rollback:
kubectl patch service ai-orchestrator-service -n ai-orchestrator \
  -p '{"spec":{"selector":{"version":"blue"}}}'
```

5. **Scale down old environment**:
```bash
# After confirming stability
kubectl scale deployment/ai-orchestrator-blue --replicas=0 -n ai-orchestrator
```

#### Rollback

Instant rollback by switching service selector:
```bash
./deployment/scripts/blue-green-switch.sh green blue
```

### Canary Deployment

Canary deployment gradually shifts traffic to new version, minimizing risk.

#### Traffic Distribution Stages

1. **10% Canary**: 1 canary pod, 5 stable pods (5 minutes monitoring)
2. **25% Canary**: 1 canary pod, 3 stable pods (10 minutes monitoring)
3. **50% Canary**: 1 canary pod, 1 stable pod (15 minutes monitoring)
4. **100% Canary**: 3 canary pods, 0 stable pods (10 minutes monitoring)

#### Deployment Process

1. **Deploy canary version**:
```bash
# Update canary deployment
kubectl set image deployment/ai-orchestrator-canary \
  ai-orchestrator=ai-orchestrator:canary \
  -n ai-orchestrator
```

2. **Automated progressive rollout**:
```bash
./deployment/scripts/canary-rollout.sh
```

The script will:
- Scale to each traffic percentage
- Monitor metrics (error rate, latency, etc.)
- Prompt for confirmation before next stage
- Automatically rollback if metrics degrade

3. **Manual canary control** (advanced):
```bash
# Stage 1: 10% traffic
kubectl scale deployment/ai-orchestrator-stable --replicas=5 -n ai-orchestrator
kubectl scale deployment/ai-orchestrator-canary --replicas=1 -n ai-orchestrator

# Monitor for 5 minutes, then proceed to next stage

# Stage 2: 25% traffic
kubectl scale deployment/ai-orchestrator-stable --replicas=3 -n ai-orchestrator
kubectl scale deployment/ai-orchestrator-canary --replicas=1 -n ai-orchestrator

# Continue...
```

#### Using Flagger (GitOps)

```bash
# Install Flagger
kubectl apply -k github.com/fluxcd/flagger//kustomize/linkerd

# Apply canary resource
kubectl apply -f deployment/kubernetes/canary-deployment.yaml

# Flagger will automatically manage traffic shifting
```

#### Rollback

```bash
# Automatic rollback on metrics degradation
# Or manual:
kubectl scale deployment/ai-orchestrator-canary --replicas=0 -n ai-orchestrator
kubectl scale deployment/ai-orchestrator-stable --replicas=5 -n ai-orchestrator
```

### Rolling Update

Standard Kubernetes rolling update with zero downtime.

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # Max pods above desired during update
    maxUnavailable: 0  # Never go below desired count
```

#### Deployment

```bash
# Update image
kubectl set image deployment/ai-orchestrator \
  ai-orchestrator=ai-orchestrator:v1.2 \
  -n ai-orchestrator

# Watch rollout
kubectl rollout status deployment/ai-orchestrator -n ai-orchestrator

# Rollback if needed
kubectl rollout undo deployment/ai-orchestrator -n ai-orchestrator
```

## Load Balancing

### HAProxy Configuration

HAProxy provides Layer 7 load balancing with advanced features:

```bash
# Deploy HAProxy
docker run -d \
  --name haproxy \
  -p 80:80 \
  -p 443:443 \
  -p 8404:8404 \
  -v $(pwd)/deployment/load-balancer/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro \
  haproxy:2.8
```

Features:
- SSL/TLS termination
- Session persistence (sticky sessions)
- Rate limiting (100 req/s per IP)
- Health checks every 10s
- Statistics dashboard at :8404/stats

### NGINX Load Balancer

```bash
# Deploy NGINX
docker run -d \
  --name nginx-lb \
  -p 80:80 \
  -p 443:443 \
  -v $(pwd)/deployment/load-balancer/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:latest
```

Features:
- HTTP/2 support
- WebSocket support
- Static content caching
- Request/response compression
- Rate limiting

### Kubernetes Ingress

```bash
# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Apply ingress configuration
kubectl apply -f deployment/kubernetes/ingress-nginx.yaml
```

## Auto-Scaling

### Horizontal Pod Autoscaler (HPA)

Automatically scales pods based on CPU/memory/custom metrics:

```bash
# Apply HPA configuration
kubectl apply -f deployment/kubernetes/hpa.yaml

# Monitor autoscaling
kubectl get hpa -n ai-orchestrator -w
```

Configuration:
- Min replicas: 3
- Max replicas: 20
- Target CPU: 70%
- Target Memory: 80%
- Scale up: aggressive (4 pods per 30s)
- Scale down: conservative (2 pods per 60s, 5min stabilization)

### Vertical Pod Autoscaler (VPA)

Automatically adjusts CPU/memory requests and limits:

```bash
# Install VPA
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v0.13.0.yaml

# Apply VPA configuration
kubectl apply -f deployment/kubernetes/hpa.yaml
```

### Cluster Autoscaler

Automatically scales cluster nodes based on pod requirements:

```bash
# For AWS EKS
eksctl create cluster \
  --name ai-orchestrator \
  --region us-west-2 \
  --nodegroup-name standard \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 20 \
  --managed \
  --asg-access

# Enable cluster autoscaler
kubectl apply -f deployment/kubernetes/cluster-autoscaler.yaml
```

## Monitoring & Alerting

### Prometheus Metrics

All deployments expose metrics on port 9090:

```prometheus
# Key metrics to monitor
- orchestrator_tasks_total
- orchestrator_task_duration_seconds
- orchestrator_agent_calls_total
- orchestrator_agent_errors_total
- orchestrator_cache_hits_total
```

### Grafana Dashboards

Import pre-configured dashboards:

```bash
# Deploy Prometheus + Grafana stack
kubectl apply -f deployment/monitoring/prometheus-stack.yaml

# Access Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

### Alerting Rules

Critical alerts configured for:
- High error rate (>5%)
- High latency (p95 >500ms)
- Pod crash loops
- Out of memory errors
- Deployment failures

## Disaster Recovery

### Backup Strategy

1. **Database backups** (if using persistent storage):
```bash
# Automated daily backups
kubectl create cronjob session-backup \
  --image=backup-tool \
  --schedule="0 2 * * *" \
  -- /backup.sh
```

2. **Configuration backups**:
```bash
# Backup all configs
kubectl get all -n ai-orchestrator -o yaml > backup-$(date +%Y%m%d).yaml
```

### Recovery Procedures

#### Full Cluster Failure
```bash
# 1. Provision new cluster
# 2. Restore configurations
kubectl apply -f backup-latest.yaml

# 3. Verify health
kubectl get pods -n ai-orchestrator
```

#### Regional Outage
- Use multi-region deployment
- DNS failover to secondary region
- RTO: < 5 minutes
- RPO: < 1 minute

## Troubleshooting

### Common Issues

#### Pod Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n ai-orchestrator

# Check logs
kubectl logs <pod-name> -n ai-orchestrator --previous

# Common causes:
# - Image pull errors
# - Resource limits
# - Configuration errors
```

#### High Latency
```bash
# Check resource usage
kubectl top pods -n ai-orchestrator

# Check HPA status
kubectl get hpa -n ai-orchestrator

# Scale manually if needed
kubectl scale deployment/ai-orchestrator --replicas=10 -n ai-orchestrator
```

#### Failed Health Checks
```bash
# Test health endpoint
kubectl exec -n ai-orchestrator <pod-name> -- curl http://localhost:5001/health

# Check recent changes
kubectl rollout history deployment/ai-orchestrator -n ai-orchestrator

# Rollback if needed
kubectl rollout undo deployment/ai-orchestrator -n ai-orchestrator
```

### Debugging Commands

```bash
# Get pod logs
kubectl logs -n ai-orchestrator -l app=ai-orchestrator --tail=100 -f

# Execute commands in pod
kubectl exec -it -n ai-orchestrator <pod-name> -- /bin/bash

# Check events
kubectl get events -n ai-orchestrator --sort-by='.lastTimestamp'

# Check resource usage
kubectl top nodes
kubectl top pods -n ai-orchestrator
```

## Jenkins CI/CD Pipeline

The Jenkinsfile provides automated deployment with:
- Code quality checks (black, flake8, mypy)
- Security scanning (bandit, trivy)
- Unit tests with coverage
- Docker image building
- Blue-green deployment to production
- Automated smoke tests
- Rollback capability

### Pipeline Stages

1. **Checkout**: Clone repository
2. **Setup**: Install dependencies
3. **Code Quality**: Parallel linting, type checking, security scans
4. **Unit Tests**: pytest with coverage reports
5. **Build**: Create Docker image with version tags
6. **Security Scan**: Trivy container scan
7. **Push**: Push to registry
8. **Deploy Staging**: Auto-deploy to staging (develop branch)
9. **Deploy Production**: Blue-green deployment (main branch)
   - Deploy to green
   - Run smoke tests
   - Manual approval
   - Switch traffic
   - Verify
   - Scale down blue
10. **Notifications**: Slack alerts on success/failure

### Running Pipeline

```bash
# Trigger via Git push
git push origin main

# Or manually via Jenkins UI
# Navigate to job and click "Build Now"
```

## Security Considerations

- All traffic encrypted with TLS 1.2+
- Rate limiting on all endpoints
- Network policies for pod-to-pod communication
- Regular security scans (Trivy, Bandit)
- Secret management via Kubernetes secrets
- RBAC for Kubernetes access
- Container security: non-root user, read-only filesystem

## Performance Tuning

### Resource Allocation
- Initial: 500m CPU, 512Mi memory
- Production: 2 CPU, 2Gi memory under load
- Use VPA for automatic optimization

### Caching
- Enable Redis for session caching
- Static asset caching via CDN
- API response caching with TTL

### Database Optimization
- Connection pooling
- Read replicas for scaling
- Regular vacuum and analyze

---

For more information, see:
- [Architecture Documentation](../ARCHITECTURE.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
