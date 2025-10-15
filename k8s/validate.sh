#!/bin/bash

# AI Nutritionist Kubernetes Configuration Validator
# This script validates the Kubernetes configurations before deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Validation functions
validate_kustomize() {
    log_info "Validating Kustomize configurations..."
    
    local errors=0
    
    # Validate base configuration
    if ! kustomize build "${K8S_DIR}/base" > /dev/null 2>&1; then
        log_error "Base Kustomize configuration is invalid"
        ((errors++))
    else
        log_success "Base configuration is valid"
    fi
    
    # Validate overlays
    for env in development staging production; do
        local overlay_dir="${K8S_DIR}/overlays/${env}"
        if [[ -d "$overlay_dir" ]]; then
            if ! kustomize build "$overlay_dir" > /dev/null 2>&1; then
                log_error "$env overlay configuration is invalid"
                ((errors++))
            else
                log_success "$env overlay is valid"
            fi
        fi
    done
    
    return $errors
}

validate_yaml_syntax() {
    log_info "Validating YAML syntax..."
    
    local errors=0
    
    # Find all YAML files
    while IFS= read -r -d '' file; do
        if ! python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            log_error "Invalid YAML syntax in: $file"
            ((errors++))
        fi
    done < <(find "$K8S_DIR" -name "*.yaml" -type f -print0)
    
    if [[ $errors -eq 0 ]]; then
        log_success "All YAML files have valid syntax"
    fi
    
    return $errors
}

validate_resource_requests() {
    log_info "Validating resource requests and limits..."
    
    local errors=0
    local warnings=0
    
    # Check each deployment for resource configuration
    while IFS= read -r -d '' file; do
        if grep -q "kind: Deployment" "$file"; then
            local deployment_name
            deployment_name=$(grep "name:" "$file" | head -1 | awk '{print $2}')
            
            if ! grep -q "resources:" "$file"; then
                log_warning "No resource limits defined in: $deployment_name"
                ((warnings++))
            fi
            
            if grep -q "resources:" "$file" && ! grep -q "requests:" "$file"; then
                log_warning "No resource requests defined in: $deployment_name"
                ((warnings++))
            fi
            
            if grep -q "resources:" "$file" && ! grep -q "limits:" "$file"; then
                log_warning "No resource limits defined in: $deployment_name"
                ((warnings++))
            fi
        fi
    done < <(find "$K8S_DIR" -name "*.yaml" -type f -print0)
    
    log_info "Found $warnings resource configuration warnings"
    return $errors
}

validate_security() {
    log_info "Validating security configurations..."
    
    local errors=0
    local warnings=0
    
    # Check for security contexts
    while IFS= read -r -d '' file; do
        if grep -q "kind: Deployment" "$file"; then
            local deployment_name
            deployment_name=$(grep "name:" "$file" | head -1 | awk '{print $2}')
            
            if ! grep -q "securityContext:" "$file"; then
                log_warning "No security context defined in: $deployment_name"
                ((warnings++))
            fi
            
            if ! grep -q "runAsNonRoot:" "$file"; then
                log_warning "runAsNonRoot not specified in: $deployment_name"
                ((warnings++))
            fi
            
            if ! grep -q "readOnlyRootFilesystem:" "$file"; then
                log_warning "readOnlyRootFilesystem not specified in: $deployment_name"
                ((warnings++))
            fi
        fi
    done < <(find "$K8S_DIR" -name "*.yaml" -type f -print0)
    
    # Check for network policies
    if ! find "$K8S_DIR" -name "*network*policy*.yaml" -type f | grep -q .; then
        log_warning "No network policies found"
        ((warnings++))
    fi
    
    # Check for pod security policies
    if ! find "$K8S_DIR" -name "*pod*security*.yaml" -type f | grep -q .; then
        log_warning "No pod security policies found"
        ((warnings++))
    fi
    
    log_info "Found $warnings security configuration warnings"
    return $errors
}

validate_health_checks() {
    log_info "Validating health check configurations..."
    
    local errors=0
    local warnings=0
    
    while IFS= read -r -d '' file; do
        if grep -q "kind: Deployment" "$file"; then
            local deployment_name
            deployment_name=$(grep "name:" "$file" | head -1 | awk '{print $2}')
            
            if ! grep -q "livenessProbe:" "$file"; then
                log_warning "No liveness probe defined in: $deployment_name"
                ((warnings++))
            fi
            
            if ! grep -q "readinessProbe:" "$file"; then
                log_warning "No readiness probe defined in: $deployment_name"
                ((warnings++))
            fi
        fi
    done < <(find "$K8S_DIR" -name "*.yaml" -type f -print0)
    
    log_info "Found $warnings health check warnings"
    return $errors
}

validate_autoscaling() {
    log_info "Validating autoscaling configurations..."
    
    local errors=0
    local warnings=0
    
    # Check for HPA configurations
    local hpa_count
    hpa_count=$(find "$K8S_DIR" -name "*.yaml" -type f -exec grep -l "kind: HorizontalPodAutoscaler" {} \; | wc -l)
    
    if [[ $hpa_count -eq 0 ]]; then
        log_warning "No Horizontal Pod Autoscalers found"
        ((warnings++))
    else
        log_success "Found $hpa_count HPA configurations"
    fi
    
    # Check for VPA configurations
    local vpa_count
    vpa_count=$(find "$K8S_DIR" -name "*.yaml" -type f -exec grep -l "kind: VerticalPodAutoscaler" {} \; | wc -l)
    
    if [[ $vpa_count -eq 0 ]]; then
        log_warning "No Vertical Pod Autoscalers found"
        ((warnings++))
    else
        log_success "Found $vpa_count VPA configurations"
    fi
    
    log_info "Found $warnings autoscaling warnings"
    return $errors
}

validate_monitoring() {
    log_info "Validating monitoring configurations..."
    
    local errors=0
    local warnings=0
    
    # Check for Prometheus annotations
    local prometheus_annotations
    prometheus_annotations=$(find "$K8S_DIR" -name "*.yaml" -type f -exec grep -l "prometheus.io/scrape" {} \; | wc -l)
    
    if [[ $prometheus_annotations -eq 0 ]]; then
        log_warning "No Prometheus scrape annotations found"
        ((warnings++))
    else
        log_success "Found Prometheus annotations in $prometheus_annotations files"
    fi
    
    # Check for monitoring stack
    if [[ -d "${K8S_DIR}/monitoring" ]]; then
        log_success "Monitoring stack configuration found"
    else
        log_warning "No monitoring stack configuration found"
        ((warnings++))
    fi
    
    log_info "Found $warnings monitoring warnings"
    return $errors
}

generate_report() {
    local total_errors=$1
    local total_warnings=$2
    
    echo
    log_info "=== VALIDATION REPORT ==="
    
    if [[ $total_errors -eq 0 ]]; then
        log_success "✅ All validations passed!"
    else
        log_error "❌ Found $total_errors errors that must be fixed"
    fi
    
    if [[ $total_warnings -gt 0 ]]; then
        log_warning "⚠️  Found $total_warnings warnings (recommended to fix)"
    else
        log_success "✅ No warnings found"
    fi
    
    echo
    log_info "Configuration Summary:"
    echo "- Base configuration: $(find "${K8S_DIR}/base" -name "*.yaml" | wc -l) files"
    echo "- Environment overlays: $(find "${K8S_DIR}/overlays" -name "*.yaml" 2>/dev/null | wc -l) files"
    echo "- Monitoring configs: $(find "${K8S_DIR}/monitoring" -name "*.yaml" 2>/dev/null | wc -l) files"
    echo "- Security policies: $(find "${K8S_DIR}/security" -name "*.yaml" 2>/dev/null | wc -l) files"
    echo "- Istio configs: $(find "${K8S_DIR}/istio" -name "*.yaml" 2>/dev/null | wc -l) files"
    
    return $total_errors
}

main() {
    log_info "Starting Kubernetes configuration validation..."
    echo
    
    local total_errors=0
    local total_warnings=0
    
    # Run validations
    validate_yaml_syntax || ((total_errors+=$?))
    echo
    
    validate_kustomize || ((total_errors+=$?))
    echo
    
    validate_resource_requests || ((total_warnings+=$?))
    echo
    
    validate_security || ((total_warnings+=$?))
    echo
    
    validate_health_checks || ((total_warnings+=$?))
    echo
    
    validate_autoscaling || ((total_warnings+=$?))
    echo
    
    validate_monitoring || ((total_warnings+=$?))
    echo
    
    generate_report $total_errors $total_warnings
    
    if [[ $total_errors -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
