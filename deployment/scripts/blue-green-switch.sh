#!/bin/bash
set -euo pipefail

# Blue-Green Deployment Switch Script
# This script handles the traffic switching between blue and green deployments

NAMESPACE="${NAMESPACE:-ai-orchestrator}"
SERVICE_NAME="${SERVICE_NAME:-ai-orchestrator-service}"
CURRENT_ENV="${1:-blue}"
TARGET_ENV="${2:-green}"

echo "================================================"
echo "Blue-Green Deployment Switcher"
echo "================================================"
echo "Namespace: $NAMESPACE"
echo "Service: $SERVICE_NAME"
echo "Current Environment: $CURRENT_ENV"
echo "Target Environment: $TARGET_ENV"
echo "================================================"

# Function to get current active environment
get_active_env() {
    kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.spec.selector.version}'
}

# Function to check deployment health
check_deployment_health() {
    local env=$1
    local deployment="ai-orchestrator-$env"

    echo "Checking health of $deployment..."

    # Check if deployment exists
    if ! kubectl get deployment "$deployment" -n "$NAMESPACE" &> /dev/null; then
        echo "❌ Deployment $deployment not found"
        return 1
    fi

    # Check if pods are ready
    local ready_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" \
        -o jsonpath='{.status.readyReplicas}')
    local desired_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" \
        -o jsonpath='{.spec.replicas}')

    echo "Ready replicas: $ready_replicas/$desired_replicas"

    if [ "$ready_replicas" != "$desired_replicas" ]; then
        echo "❌ Not all replicas are ready"
        return 1
    fi

    echo "✅ All replicas are healthy"
    return 0
}

# Function to run health checks
run_health_checks() {
    local env=$1
    local pod=$(kubectl get pods -n "$NAMESPACE" \
        -l "app=ai-orchestrator,version=$env" \
        -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$pod" ]; then
        echo "❌ No pods found for environment $env"
        return 1
    fi

    echo "Running health checks on pod $pod..."

    # Check health endpoint
    if kubectl exec -n "$NAMESPACE" "$pod" -- curl -sf http://localhost:5001/health > /dev/null; then
        echo "✅ Health check passed"
    else
        echo "❌ Health check failed"
        return 1
    fi

    # Check readiness endpoint
    if kubectl exec -n "$NAMESPACE" "$pod" -- curl -sf http://localhost:5001/ready > /dev/null; then
        echo "✅ Readiness check passed"
    else
        echo "❌ Readiness check failed"
        return 1
    fi

    return 0
}

# Function to switch traffic
switch_traffic() {
    local from=$1
    local to=$2

    echo ""
    echo "Switching traffic from $from to $to..."

    # Patch the service selector
    kubectl patch service "$SERVICE_NAME" -n "$NAMESPACE" \
        -p "{\"spec\":{\"selector\":{\"version\":\"$to\"}}}"

    echo "✅ Traffic switched to $to environment"
}

# Function to rollback
rollback() {
    echo ""
    echo "🔄 Rolling back to $CURRENT_ENV..."
    switch_traffic "$TARGET_ENV" "$CURRENT_ENV"
    echo "✅ Rollback completed"
}

# Main execution
main() {
    echo ""
    echo "Step 1: Verifying current environment"
    ACTIVE_ENV=$(get_active_env)
    echo "Current active environment: $ACTIVE_ENV"

    if [ "$ACTIVE_ENV" != "$CURRENT_ENV" ]; then
        echo "⚠️  Warning: Active environment ($ACTIVE_ENV) doesn't match expected ($CURRENT_ENV)"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted"
            exit 1
        fi
    fi

    echo ""
    echo "Step 2: Checking target environment health"
    if ! check_deployment_health "$TARGET_ENV"; then
        echo "❌ Target environment is not healthy. Aborting."
        exit 1
    fi

    echo ""
    echo "Step 3: Running health checks on target environment"
    if ! run_health_checks "$TARGET_ENV"; then
        echo "❌ Health checks failed. Aborting."
        exit 1
    fi

    echo ""
    echo "Step 4: Switching traffic"
    echo "⚠️  WARNING: This will switch production traffic to $TARGET_ENV"
    read -p "Are you sure you want to continue? (yes/no) " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Aborted"
        exit 1
    fi

    switch_traffic "$CURRENT_ENV" "$TARGET_ENV"

    echo ""
    echo "Step 5: Monitoring new environment (30s)"
    echo "Watching for errors..."
    sleep 5

    # Quick validation
    if ! run_health_checks "$TARGET_ENV"; then
        echo "❌ Post-switch health check failed!"
        rollback
        exit 1
    fi

    echo ""
    echo "Waiting 25 more seconds for traffic stabilization..."
    sleep 25

    # Final validation
    if ! run_health_checks "$TARGET_ENV"; then
        echo "❌ Final health check failed!"
        rollback
        exit 1
    fi

    echo ""
    echo "================================================"
    echo "✅ Blue-Green deployment completed successfully!"
    echo "================================================"
    echo "Active environment: $TARGET_ENV"
    echo ""
    echo "Next steps:"
    echo "1. Monitor metrics and logs"
    echo "2. Scale down $CURRENT_ENV deployment if satisfied"
    echo "3. Keep $CURRENT_ENV ready for quick rollback"
    echo ""
    echo "To rollback:"
    echo "  ./blue-green-switch.sh $TARGET_ENV $CURRENT_ENV"
    echo ""
}

# Trap errors and rollback
trap 'rollback; exit 1' ERR

# Run main function
main
