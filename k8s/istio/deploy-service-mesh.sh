#!/bin/bash

# AI Nutritionist Service Mesh Deployment Script
# Comprehensive Istio configuration with traffic management, security, and observability

set -euo pipefail

# Configuration
NAMESPACE="ai-nutritionist"
ISTIO_NAMESPACE="istio-system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check if istioctl is installed
    if ! command -v istioctl &> /dev/null; then
        log_error "istioctl is not installed"
        exit 1
    fi
    
    # Check Kubernetes connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check Istio version
    ISTIO_VERSION=$(istioctl version --short 2>/dev/null | grep client | awk '{print $NF}' || echo "unknown")
    log_info "Istio version: $ISTIO_VERSION"
    
    log_success "Prerequisites check completed"
}

# Install Istio if not present
install_istio() {
    log_info "Checking Istio installation..."
    
    if ! kubectl get namespace $ISTIO_NAMESPACE &> /dev/null; then
        log_info "Installing Istio..."
        istioctl install --set values.defaultRevision=default -y
        
        # Wait for Istio to be ready
        kubectl wait --for=condition=ready pod -l app=istiod -n $ISTIO_NAMESPACE --timeout=300s
        log_success "Istio installation completed"
    else
        log_info "Istio is already installed"
    fi
}

# Create namespace and enable injection
setup_namespace() {
    log_info "Setting up namespace..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        kubectl create namespace $NAMESPACE
        log_success "Created namespace: $NAMESPACE"
    fi
    
    # Enable sidecar injection
    kubectl label namespace $NAMESPACE istio-injection=enabled --overwrite
    log_success "Enabled Istio sidecar injection for namespace: $NAMESPACE"
}

# Deploy service mesh configuration
deploy_service_mesh() {
    log_info "Deploying service mesh configuration..."
    
    # Apply enhanced Istio configuration
    kubectl apply -f "$SCRIPT_DIR/service-mesh-complete.yaml"
    log_success "Applied complete service mesh configuration"
    
    # Wait for gateway to be ready
    kubectl wait --for=condition=programmed gateway/ai-nutritionist-gateway-enhanced -n $NAMESPACE --timeout=300s
    
    log_success "Service mesh configuration deployed"
}

# Deploy security policies
deploy_security() {
    log_info "Deploying security policies..."
    
    kubectl apply -f "$SCRIPT_DIR/security-policies-enhanced.yaml"
    
    # Wait for policies to be applied
    sleep 30
    
    log_success "Security policies deployed"
}

# Deploy traffic management
deploy_traffic_management() {
    log_info "Deploying traffic management configurations..."
    
    kubectl apply -f "$SCRIPT_DIR/traffic-management-advanced.yaml"
    
    log_success "Traffic management configurations deployed"
}

# Deploy observability stack
deploy_observability() {
    log_info "Deploying observability stack..."
    
    # Apply observability configurations
    kubectl apply -f "$SCRIPT_DIR/observability-complete.yaml"
    
    # Install Prometheus if not present
    if ! kubectl get deployment prometheus -n $ISTIO_NAMESPACE &> /dev/null; then
        log_info "Installing Prometheus..."
        kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/prometheus.yaml
    fi
    
    # Install Grafana if not present
    if ! kubectl get deployment grafana -n $ISTIO_NAMESPACE &> /dev/null; then
        log_info "Installing Grafana..."
        kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/grafana.yaml
    fi
    
    # Install Jaeger if not present
    if ! kubectl get deployment jaeger -n $ISTIO_NAMESPACE &> /dev/null; then
        log_info "Installing Jaeger..."
        kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/jaeger.yaml
    fi
    
    # Install Kiali if not present
    if ! kubectl get deployment kiali -n $ISTIO_NAMESPACE &> /dev/null; then
        log_info "Installing Kiali..."
        kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/kiali.yaml
    fi
    
    log_success "Observability stack deployed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check Istio components
    log_info "Checking Istio components..."
    kubectl get pods -n $ISTIO_NAMESPACE
    
    # Check service mesh status
    log_info "Checking service mesh status..."
    istioctl proxy-status
    
    # Check gateway status
    log_info "Checking gateway status..."
    kubectl get gateway -n $NAMESPACE
    
    # Check virtual services
    log_info "Checking virtual services..."
    kubectl get virtualservice -n $NAMESPACE
    
    # Check destination rules
    log_info "Checking destination rules..."
    kubectl get destinationrule -n $NAMESPACE
    
    # Check security policies
    log_info "Checking security policies..."
    kubectl get peerauthentication,authorizationpolicy -n $NAMESPACE
    
    log_success "Deployment verification completed"
}

# Generate access URLs
generate_access_urls() {
    log_info "Generating access URLs..."
    
    # Get ingress gateway external IP
    INGRESS_HOST=$(kubectl get service istio-ingressgateway -n $ISTIO_NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "localhost")
    if [ "$INGRESS_HOST" = "" ]; then
        INGRESS_HOST=$(kubectl get service istio-ingressgateway -n $ISTIO_NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "localhost")
    fi
    
    INGRESS_PORT=$(kubectl get service istio-ingressgateway -n $ISTIO_NAMESPACE -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
    SECURE_INGRESS_PORT=$(kubectl get service istio-ingressgateway -n $ISTIO_NAMESPACE -o jsonpath='{.spec.ports[?(@.name=="https")].port}')
    
    echo ""
    log_success "🚀 AI Nutritionist Service Mesh Deployed Successfully!"
    echo ""
    echo "📊 Access URLs:"
    echo "  • Gateway: http://$INGRESS_HOST:$INGRESS_PORT"
    echo "  • Gateway (HTTPS): https://$INGRESS_HOST:$SECURE_INGRESS_PORT"
    echo ""
    echo "🔍 Observability Tools:"
    echo "  • Grafana: kubectl port-forward -n istio-system svc/grafana 3000:3000"
    echo "  • Jaeger: kubectl port-forward -n istio-system svc/jaeger 16686:16686"
    echo "  • Kiali: kubectl port-forward -n istio-system svc/kiali 20001:20001"
    echo "  • Prometheus: kubectl port-forward -n istio-system svc/prometheus 9090:9090"
    echo ""
    echo "🛠️  Management Commands:"
    echo "  • View mesh status: istioctl proxy-status"
    echo "  • View configuration: istioctl proxy-config cluster <pod-name> -n $NAMESPACE"
    echo "  • View metrics: kubectl top pods -n $NAMESPACE"
    echo ""
}

# Cleanup function
cleanup() {
    log_warning "Cleaning up service mesh configuration..."
    
    read -p "Are you sure you want to remove the service mesh configuration? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete -f "$SCRIPT_DIR/observability-complete.yaml" --ignore-not-found
        kubectl delete -f "$SCRIPT_DIR/traffic-management-advanced.yaml" --ignore-not-found
        kubectl delete -f "$SCRIPT_DIR/security-policies-enhanced.yaml" --ignore-not-found
        kubectl delete -f "$SCRIPT_DIR/service-mesh-complete.yaml" --ignore-not-found
        
        log_success "Service mesh configuration removed"
    else
        log_info "Cleanup cancelled"
    fi
}

# Test connectivity
test_connectivity() {
    log_info "Testing service mesh connectivity..."
    
    # Deploy test pod if not exists
    if ! kubectl get pod test-connectivity -n $NAMESPACE &> /dev/null; then
        kubectl run test-connectivity -n $NAMESPACE --image=curlimages/curl:latest --rm -it --restart=Never -- /bin/sh -c "
            echo 'Testing internal service connectivity...'
            curl -s -o /dev/null -w '%{http_code}' nutrition-service.$NAMESPACE.svc.cluster.local:8080/health || echo 'Failed'
            curl -s -o /dev/null -w '%{http_code}' ai-coach-service.$NAMESPACE.svc.cluster.local:8080/health || echo 'Failed'
            curl -s -o /dev/null -w '%{http_code}' messaging-service.$NAMESPACE.svc.cluster.local:8080/health || echo 'Failed'
            echo 'Connectivity test completed'
        "
    fi
}

# Main execution
main() {
    case "${1:-deploy}" in
        "deploy")
            log_info "🚀 Starting AI Nutritionist Service Mesh Deployment"
            check_prerequisites
            install_istio
            setup_namespace
            deploy_service_mesh
            deploy_security
            deploy_traffic_management
            deploy_observability
            verify_deployment
            generate_access_urls
            ;;
        "cleanup")
            cleanup
            ;;
        "verify")
            verify_deployment
            ;;
        "test")
            test_connectivity
            ;;
        "urls")
            generate_access_urls
            ;;
        *)
            echo "Usage: $0 {deploy|cleanup|verify|test|urls}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Deploy complete service mesh configuration"
            echo "  cleanup  - Remove service mesh configuration"
            echo "  verify   - Verify current deployment status"
            echo "  test     - Test service connectivity"
            echo "  urls     - Show access URLs"
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"
