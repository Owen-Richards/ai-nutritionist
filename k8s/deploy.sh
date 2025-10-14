#!/bin/bash

# AI Nutritionist Kubernetes Deployment Script
# This script deploys the AI Nutritionist platform to Kubernetes

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}"
DEFAULT_ENVIRONMENT="development"
DEFAULT_NAMESPACE="ai-nutritionist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Help function
show_help() {
    cat << EOF
AI Nutritionist Kubernetes Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV    Environment to deploy (development, staging, production)
    -n, --namespace NS       Kubernetes namespace (default: ai-nutritionist)
    -i, --install-istio      Install Istio service mesh
    -m, --install-monitoring Install monitoring stack (Prometheus, Grafana, Jaeger)
    -d, --dry-run           Show what would be deployed without applying
    -c, --cleanup           Cleanup deployment
    -h, --help              Show this help message

EXAMPLES:
    $0 -e development                    # Deploy to development
    $0 -e production -i -m              # Deploy to production with Istio and monitoring
    $0 --dry-run -e staging             # Preview staging deployment
    $0 --cleanup -e development         # Cleanup development deployment

EOF
}

# Parse command line arguments
parse_args() {
    ENVIRONMENT="${DEFAULT_ENVIRONMENT}"
    NAMESPACE="${DEFAULT_NAMESPACE}"
    INSTALL_ISTIO=false
    INSTALL_MONITORING=false
    DRY_RUN=false
    CLEANUP=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -i|--install-istio)
                INSTALL_ISTIO=true
                shift
                ;;
            -m|--install-monitoring)
                INSTALL_MONITORING=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -c|--cleanup)
                CLEANUP=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        log_error "Valid environments: development, staging, production"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    # Check kustomize
    if ! command -v kustomize &> /dev/null; then
        log_error "kustomize not found. Please install kustomize."
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi

    # Check if Istio is available if requested
    if [[ "$INSTALL_ISTIO" == true ]]; then
        if ! command -v istioctl &> /dev/null; then
            log_error "istioctl not found. Please install Istio CLI."
            exit 1
        fi
    fi

    log_success "Prerequisites check passed"
}

# Install Istio service mesh
install_istio() {
    if [[ "$INSTALL_ISTIO" != true ]]; then
        return 0
    fi

    log_info "Installing Istio service mesh..."

    # Install Istio operator
    istioctl operator init

    # Wait for operator to be ready
    kubectl wait --for=condition=available --timeout=600s deployment/istio-operator -n istio-operator

    # Apply Istio configuration
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would apply Istio configuration"
        cat "${K8S_DIR}/istio/istio-config.yaml"
    else
        kubectl apply -f "${K8S_DIR}/istio/istio-config.yaml"
        
        # Wait for Istio to be ready
        kubectl wait --for=condition=available --timeout=600s deployment/istiod -n istio-system
        kubectl wait --for=condition=available --timeout=600s deployment/istio-ingressgateway -n istio-system
    fi

    log_success "Istio installation completed"
}

# Install monitoring stack
install_monitoring() {
    if [[ "$INSTALL_MONITORING" != true ]]; then
        return 0
    fi

    log_info "Installing monitoring stack..."

    # Create monitoring namespace
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would create monitoring namespace"
    else
        kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    fi

    # Apply monitoring configurations
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would apply monitoring configurations"
        kustomize build "${K8S_DIR}/monitoring"
    else
        kustomize build "${K8S_DIR}/monitoring" | kubectl apply -f -
        
        # Wait for monitoring stack to be ready
        kubectl wait --for=condition=available --timeout=600s deployment/prometheus -n ai-nutritionist
        kubectl wait --for=condition=available --timeout=600s deployment/grafana -n ai-nutritionist
        kubectl wait --for=condition=available --timeout=600s deployment/jaeger-query -n ai-nutritionist
    fi

    log_success "Monitoring stack installation completed"
}

# Deploy application
deploy_application() {
    log_info "Deploying AI Nutritionist application to $ENVIRONMENT environment..."

    # Create namespace
    local namespace_env="${NAMESPACE}"
    if [[ "$ENVIRONMENT" != "production" ]]; then
        namespace_env="${NAMESPACE}-${ENVIRONMENT}"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would create namespace: $namespace_env"
    else
        kubectl create namespace "$namespace_env" --dry-run=client -o yaml | kubectl apply -f -
    fi

    # Apply environment-specific configuration
    local overlay_dir="${K8S_DIR}/overlays/${ENVIRONMENT}"
    
    if [[ ! -d "$overlay_dir" ]]; then
        log_error "Environment overlay directory not found: $overlay_dir"
        exit 1
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would apply configurations for $ENVIRONMENT"
        kustomize build "$overlay_dir"
    else
        kustomize build "$overlay_dir" | kubectl apply -f -
        
        # Wait for core services to be ready
        log_info "Waiting for services to be ready..."
        kubectl wait --for=condition=available --timeout=600s deployment/nutrition-service -n "$namespace_env"
        kubectl wait --for=condition=available --timeout=600s deployment/ai-coach-service -n "$namespace_env"
        kubectl wait --for=condition=available --timeout=600s deployment/messaging-service -n "$namespace_env"
        kubectl wait --for=condition=available --timeout=600s deployment/web-app -n "$namespace_env"
    fi

    # Apply Istio security policies
    if [[ "$INSTALL_ISTIO" == true ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            log_info "DRY RUN: Would apply Istio security policies"
            cat "${K8S_DIR}/istio/security-policies.yaml"
        else
            kubectl apply -f "${K8S_DIR}/istio/security-policies.yaml"
        fi
    fi

    log_success "Application deployment completed"
}

# Cleanup deployment
cleanup_deployment() {
    if [[ "$CLEANUP" != true ]]; then
        return 0
    fi

    log_warning "Cleaning up deployment for $ENVIRONMENT environment..."

    local namespace_env="${NAMESPACE}"
    if [[ "$ENVIRONMENT" != "production" ]]; then
        namespace_env="${NAMESPACE}-${ENVIRONMENT}"
    fi

    # Confirm cleanup for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        read -p "Are you sure you want to cleanup PRODUCTION environment? (yes/no): " confirmation
        if [[ "$confirmation" != "yes" ]]; then
            log_info "Cleanup cancelled"
            exit 0
        fi
    fi

    # Delete application resources
    local overlay_dir="${K8S_DIR}/overlays/${ENVIRONMENT}"
    if [[ -d "$overlay_dir" ]]; then
        kustomize build "$overlay_dir" | kubectl delete -f - --ignore-not-found=true
    fi

    # Delete namespace
    kubectl delete namespace "$namespace_env" --ignore-not-found=true

    log_success "Cleanup completed"
}

# Get deployment status
get_status() {
    log_info "Getting deployment status for $ENVIRONMENT environment..."

    local namespace_env="${NAMESPACE}"
    if [[ "$ENVIRONMENT" != "production" ]]; then
        namespace_env="${NAMESPACE}-${ENVIRONMENT}"
    fi

    # Check if namespace exists
    if ! kubectl get namespace "$namespace_env" &> /dev/null; then
        log_warning "Namespace $namespace_env not found"
        return 1
    fi

    echo
    log_info "Deployments:"
    kubectl get deployments -n "$namespace_env" -o wide

    echo
    log_info "Services:"
    kubectl get services -n "$namespace_env" -o wide

    echo
    log_info "Pods:"
    kubectl get pods -n "$namespace_env" -o wide

    echo
    log_info "HPA Status:"
    kubectl get hpa -n "$namespace_env" -o wide

    # Show Istio status if installed
    if kubectl get namespace istio-system &> /dev/null; then
        echo
        log_info "Istio Status:"
        kubectl get pods -n istio-system
    fi

    # Show monitoring status if installed
    if kubectl get deployment prometheus -n ai-nutritionist &> /dev/null; then
        echo
        log_info "Monitoring Status:"
        kubectl get pods -n ai-nutritionist -l component=monitoring
    fi
}

# Main function
main() {
    parse_args "$@"

    log_info "AI Nutritionist Kubernetes Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Namespace: $NAMESPACE"
    log_info "Istio: $INSTALL_ISTIO"
    log_info "Monitoring: $INSTALL_MONITORING"
    log_info "Dry Run: $DRY_RUN"
    log_info "Cleanup: $CLEANUP"
    echo

    if [[ "$CLEANUP" == true ]]; then
        cleanup_deployment
        exit 0
    fi

    check_prerequisites
    install_istio
    install_monitoring
    deploy_application
    
    if [[ "$DRY_RUN" != true ]]; then
        get_status
        
        echo
        log_success "Deployment completed successfully!"
        log_info "You can check the status with: $0 -e $ENVIRONMENT --status"
        
        if [[ "$INSTALL_MONITORING" == true ]]; then
            log_info "Grafana dashboard: kubectl port-forward svc/grafana-service 3000:3000 -n ai-nutritionist"
            log_info "Prometheus: kubectl port-forward svc/prometheus-service 9090:9090 -n ai-nutritionist"
            log_info "Jaeger: kubectl port-forward svc/jaeger-query 16686:16686 -n ai-nutritionist"
        fi
    else
        log_info "Dry run completed. Use without --dry-run to apply changes."
    fi
}

# Run main function
main "$@"
