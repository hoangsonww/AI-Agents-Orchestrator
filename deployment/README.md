# Deployment Infrastructure

This directory contains all production deployment configurations and scripts for the AI Agents Orchestrator.

## 📁 Directory Structure

```
deployment/
├── README.md                    # This file
├── DEPLOYMENT.md               # Comprehensive deployment guide
├── kubernetes/                 # Kubernetes manifests
│   ├── deployment.yaml        # Basic deployment
│   ├── service.yaml           # Service configuration
│   ├── configmap.yaml         # Configuration
│   ├── pvc.yaml              # Persistent volumes
│   ├── blue-green-deployment.yaml   # Blue/Green setup
│   ├── canary-deployment.yaml       # Canary setup with Flagger
│   ├── ingress-nginx.yaml           # Ingress + TLS
│   └── hpa.yaml                     # Auto-scaling
├── load-balancer/             # Load balancer configs
│   ├── haproxy.cfg           # HAProxy configuration
│   └── nginx.conf            # NGINX configuration
├── scripts/                   # Deployment automation
│   ├── blue-green-switch.sh  # Blue/Green switcher
│   └── canary-rollout.sh     # Canary rollout
└── systemd/                   # Systemd service files
```

## 🚀 Quick Start

### 1. Blue-Green Deployment

```bash
# Deploy to green environment
kubectl apply -f kubernetes/blue-green-deployment.yaml

# Switch traffic from blue to green
./scripts/blue-green-switch.sh blue green

# Rollback if needed
./scripts/blue-green-switch.sh green blue
```

### 2. Canary Deployment

```bash
# Apply canary configuration
kubectl apply -f kubernetes/canary-deployment.yaml

# Run progressive canary rollout (10% → 25% → 50% → 100%)
./scripts/canary-rollout.sh
```

### 3. Load Balancer Setup

#### HAProxy
```bash
docker run -d \
  --name haproxy-lb \
  -p 80:80 -p 443:443 -p 8404:8404 \
  -v $(pwd)/load-balancer/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro \
  haproxy:2.8
```

#### NGINX
```bash
docker run -d \
  --name nginx-lb \
  -p 80:80 -p 443:443 \
  -v $(pwd)/load-balancer/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:latest
```

## 🔧 CI/CD Pipelines

### Jenkins

The project includes a complete Jenkinsfile at the root with:
- Automated testing and quality checks
- Docker image building and scanning
- Blue-green deployment to production
- Automated rollback on failure

```bash
# Jenkinsfile is at: ../../Jenkinsfile
```

### GitLab CI

Configuration file: `../.gitlab-ci.yml`

Pipeline stages:
1. **test**: Linting, type checking, security scans, unit tests
2. **build**: Docker image creation and security scanning
3. **deploy**: Staging (auto) + Production (manual approval)
4. **verify**: Smoke tests

### CircleCI

Configuration file: `../.circleci/config.yml`

Features:
- Parallel test execution
- Docker layer caching
- Manual approval gates
- Slack notifications

## 📊 Deployment Strategies

### Blue-Green Deployment

**When to use**: Production releases requiring instant rollback capability

**Process**:
1. Deploy new version to inactive environment (green)
2. Run health checks and smoke tests
3. Switch traffic to green
4. Keep blue ready for instant rollback
5. Scale down blue after validation

**Rollback time**: < 10 seconds

### Canary Deployment

**When to use**: High-risk changes, gradual rollouts, A/B testing

**Process**:
1. Deploy canary version alongside stable
2. Route 10% of traffic to canary
3. Monitor metrics for 5-10 minutes
4. Progressively increase: 10% → 25% → 50% → 100%
5. Automatic rollback if metrics degrade

**Rollback time**: < 30 seconds (automatic)

### Rolling Update

**When to use**: Regular updates with minimal risk

**Process**:
1. Update deployment image
2. Kubernetes replaces pods gradually
3. Health checks ensure readiness
4. Built-in rollback capability

**Rollback time**: 1-2 minutes

## 🔍 Monitoring & Observability

### Health Endpoints

- `/health` - Liveness probe
- `/ready` - Readiness probe
- `/metrics` - Prometheus metrics

### Key Metrics

```prometheus
# Request metrics
orchestrator_tasks_total
orchestrator_task_duration_seconds
orchestrator_agent_calls_total

# Error metrics
orchestrator_agent_errors_total
orchestrator_task_failures_total

# Resource metrics
orchestrator_cache_hits_total
orchestrator_cache_misses_total
```

### Dashboards

- HAProxy Stats: `http://your-lb:8404/stats`
- NGINX Status: `http://your-lb:8080/nginx_status`
- Grafana: `http://your-monitoring:3000`
- Prometheus: `http://your-monitoring:9090`

## ⚡ Auto-Scaling

### Horizontal Pod Autoscaler (HPA)

Configured in `kubernetes/hpa.yaml`:
- Min replicas: 3
- Max replicas: 20
- Target CPU: 70%
- Target Memory: 80%

### Vertical Pod Autoscaler (VPA)

Automatically adjusts resource requests/limits based on usage.

### Cluster Autoscaler

Automatically scales node count based on pod requirements.

## 🔐 Security

### TLS/SSL Configuration

- TLS 1.2+ only
- Strong cipher suites
- HSTS enabled
- Certificate auto-renewal via cert-manager

### Rate Limiting

- Per-IP: 100 requests/second
- Login endpoints: 5 requests/second
- WebSocket connections: 50 concurrent per IP

### Network Policies

```bash
# Apply network policies
kubectl apply -f kubernetes/network-policies.yaml
```

## 📝 Common Tasks

### View Current Deployment

```bash
# Check which environment is active
kubectl get service ai-orchestrator-service -n ai-orchestrator \
  -o jsonpath='{.spec.selector.version}'

# Check pod status
kubectl get pods -n ai-orchestrator -l app=ai-orchestrator
```

### Scale Deployment

```bash
# Manual scaling
kubectl scale deployment/ai-orchestrator-blue --replicas=5 -n ai-orchestrator

# HPA will override manual scaling
```

### View Logs

```bash
# All pods
kubectl logs -n ai-orchestrator -l app=ai-orchestrator --tail=100 -f

# Specific pod
kubectl logs -n ai-orchestrator <pod-name> -f

# Previous pod (after crash)
kubectl logs -n ai-orchestrator <pod-name> --previous
```

### Execute Commands

```bash
# Shell into pod
kubectl exec -it -n ai-orchestrator <pod-name> -- /bin/bash

# Run health check
kubectl exec -n ai-orchestrator <pod-name> -- curl http://localhost:5001/health
```

### Update Configuration

```bash
# Edit configmap
kubectl edit configmap ai-orchestrator-config -n ai-orchestrator

# Restart pods to pick up changes
kubectl rollout restart deployment/ai-orchestrator-blue -n ai-orchestrator
```

## 🆘 Troubleshooting

### Pod Not Starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n ai-orchestrator

# Common issues:
# - ImagePullBackOff: Check image name/tag
# - CrashLoopBackOff: Check logs
# - Pending: Check resources/node capacity
```

### High Latency

```bash
# Check HPA status
kubectl get hpa -n ai-orchestrator

# Check resource usage
kubectl top pods -n ai-orchestrator

# Scale up manually if needed
kubectl scale deployment/ai-orchestrator-blue --replicas=10 -n ai-orchestrator
```

### Failed Deployment

```bash
# Check rollout status
kubectl rollout status deployment/ai-orchestrator-blue -n ai-orchestrator

# View rollout history
kubectl rollout history deployment/ai-orchestrator-blue -n ai-orchestrator

# Rollback to previous version
kubectl rollout undo deployment/ai-orchestrator-blue -n ai-orchestrator
```

## 📚 Additional Resources

- [Complete Deployment Guide](./DEPLOYMENT.md)
- [Architecture Documentation](../ARCHITECTURE.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [HAProxy Documentation](http://www.haproxy.org/#docs)
- [NGINX Documentation](https://nginx.org/en/docs/)

## 💬 Support

For deployment issues:
1. Check [DEPLOYMENT.md](./DEPLOYMENT.md) troubleshooting section
2. Review logs: `kubectl logs -n ai-orchestrator -l app=ai-orchestrator`
3. Check metrics in Grafana
4. Open an issue on GitHub

## 🔄 Version History

- **v1.0.0**: Initial production release
  - Blue-Green deployment
  - Basic monitoring
  - Manual scaling

- **v1.1.0**: Enhanced deployment features
  - Canary deployment with Flagger
  - HPA/VPA auto-scaling
  - Advanced load balancing
  - Multiple CI/CD options (Jenkins, GitLab, CircleCI)
