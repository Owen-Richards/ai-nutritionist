# AI Nutritionist Service Mesh Implementation

This document provides comprehensive documentation for the Istio service mesh implementation for the AI Nutritionist platform, including traffic management, security, and observability features.

## 🏗️ Architecture Overview

The service mesh implementation provides:

1. **Service Discovery & Load Balancing**: Automatic service discovery with multiple load balancing algorithms
2. **Traffic Management**: Canary deployments, A/B testing, blue-green deployments, and traffic splitting
3. **Security**: mTLS, JWT validation, authorization policies, and rate limiting
4. **Observability**: Distributed tracing, metrics collection, and performance monitoring

## 📁 File Structure

```
k8s/istio/
├── service-mesh-complete.yaml         # Complete Istio configuration
├── security-policies-enhanced.yaml    # Enhanced security policies
├── traffic-management-advanced.yaml   # Advanced traffic management
├── observability-complete.yaml        # Comprehensive observability
├── deploy-service-mesh.sh             # Deployment script
└── README.md                          # This documentation
```

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (1.26+)
- kubectl configured
- Istio CLI (1.20+)
- Sufficient cluster resources (4+ CPU cores, 8GB+ RAM)

### Deployment

```bash
# Deploy the complete service mesh
./deploy-service-mesh.sh deploy

# Verify deployment
./deploy-service-mesh.sh verify

# Test connectivity
./deploy-service-mesh.sh test

# Get access URLs
./deploy-service-mesh.sh urls

# Cleanup (if needed)
./deploy-service-mesh.sh cleanup
```

## 🔧 Configuration Details

### 1. Service Discovery & Load Balancing

The service mesh automatically discovers services and provides multiple load balancing strategies:

#### Load Balancing Algorithms

- **ROUND_ROBIN**: Default for messaging service
- **LEAST_CONN**: Used for nutrition and health tracking services
- **RANDOM**: Available for testing scenarios
- **CONSISTENT_HASH**: User-based routing for nutrition service

#### Connection Pooling

```yaml
connectionPool:
  tcp:
    maxConnections: 100-500 # Service dependent
    connectTimeout: 10-30s
  http:
    http1MaxPendingRequests: 25-100
    http2MaxRequests: 50-200
    maxRequestsPerConnection: 1-20
    maxRetries: 1-3
```

### 2. Traffic Management

#### Canary Deployments

**Nutrition Service Example:**

- Beta users get 100% canary traffic
- Gradual rollout with 5% traffic split
- Automatic failback on high error rates

```bash
# Enable canary for specific users
curl -H "x-user-tier: beta" -H "x-canary-enabled: true" api.ai-nutritionist.com/api/v1/nutrition
```

#### A/B Testing

**AI Coach Service Example:**

- Algorithm A vs Algorithm B testing
- Premium feature testing
- Automatic traffic splitting (50/50 or custom)

```bash
# Trigger A/B test
curl -H "x-ab-test: nutrition-algorithm" api.ai-nutritionist.com/api/v1/ai-coach
```

#### Blue-Green Deployments

**Payment Service Example:**

- Blue: Production environment
- Green: Staging/testing environment
- Instant traffic switching

```bash
# Route to green deployment
curl -H "x-deployment-target: green" -H "x-testing-mode: enabled" api.ai-nutritionist.com/api/v1/payments
```

#### Feature Flags

Dynamic feature enabling based on headers:

- `x-feature-flag-new-provider: enabled`
- `x-feature-flag-enhanced-messaging: enabled`
- User segment-based routing

### 3. Security Implementation

#### mTLS (Mutual TLS)

**Strict Mode**: All service-to-service communication encrypted

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default-mtls
spec:
  mtls:
    mode: STRICT
```

#### JWT Authentication

Multiple identity providers supported:

- Internal auth: `https://auth.ai-nutritionist.com`
- Google OAuth: `https://accounts.google.com`
- Apple Sign-in: `https://appleid.apple.com`

**Required Headers:**

- `Authorization: Bearer <jwt_token>`
- `x-user-verified: true` (for payments)

#### Authorization Policies

**Service-Specific Rules:**

- **Nutrition Service**: Authenticated users + internal services
- **AI Coach Service**: Premium users only
- **Payment Service**: Verified users with enhanced security
- **Messaging Service**: Authenticated users + webhook access

#### Rate Limiting

**Global Rate Limits:**

- 1000 tokens max, 100 tokens/minute refill
- Service-specific limits for AI Coach (100 tokens, 10/minute)

### 4. Circuit Breaking & Resilience

#### Circuit Breaker Configuration

**AI Coach Service (Most Restrictive):**

```yaml
connectionPool:
  tcp:
    maxConnections: 50
  http:
    http1MaxPendingRequests: 25
    maxRetries: 2
outlierDetection:
  consecutiveGatewayErrors: 3
  consecutive5xxErrors: 3
  interval: 15s
  baseEjectionTime: 15s
  maxEjectionPercent: 30
```

**Payment Service (Ultra-Strict):**

```yaml
connectionPool:
  tcp:
    maxConnections: 50
    connectTimeout: 10s
  http:
    maxRequestsPerConnection: 1 # No connection reuse
    maxRetries: 1 # Minimal retries
outlierDetection:
  consecutiveGatewayErrors: 2 # Fast ejection
  maxEjectionPercent: 25 # Conservative ejection
```

#### Retry Policies

**Service-Specific Timeouts:**

- AI Coach: 120s timeout, 2 retries
- Payment: 30s timeout, 1 retry
- Nutrition: 60s timeout, 3 retries
- Health: 45s timeout, 2 retries

### 5. Observability Stack

#### Metrics Collection

**RED Metrics (Rate, Errors, Duration):**

- Request rate by service
- Error rate by service
- Latency percentiles (P50, P95, P99)

**Business Metrics:**

- Active users count
- Premium user requests
- Canary deployment metrics
- Circuit breaker status

#### Distributed Tracing

**Jaeger Configuration:**

- Production-grade with Elasticsearch storage
- 7-day retention with automatic cleanup
- Header propagation for request correlation

**Trace Headers:**

- `x-request-id`: Request correlation
- `x-user-id`: User-specific tracing
- `x-deployment-version`: Version tracking

#### Alerting Rules

**Critical Alerts:**

- Error rate > 5% for 5 minutes
- P99 latency > 5000ms for 5 minutes
- Request rate < 0.1 req/sec for 10 minutes
- Canary error rate > 10% for 2 minutes

#### Dashboards

**Grafana Dashboards:**

1. Service Mesh Overview
2. Performance Monitoring
3. Security Metrics
4. Business KPIs

## 🌍 Geographic & Compliance Routing

### Data Residency

**EU/GDPR Routing:**

```yaml
- match:
    - headers:
        cloudfront-viewer-country:
          regex: "DE|FR|IT|ES|NL|BE|AT|PT|PL|CZ|HU|SK|SI|HR|BG|RO|GR|CY|MT|LU|LV|LT|EE|FI|SE|DK|IE"
  route:
    - destination:
        host: health-tracking-service
        subset: eu-gdpr
```

**US/HIPAA Routing:**

```yaml
- match:
    - headers:
        cloudfront-viewer-country:
          exact: "US"
  route:
    - destination:
        host: health-tracking-service
        subset: us
```

## 🧪 Testing & Validation

### Connectivity Testing

```bash
# Test internal service connectivity
kubectl run test-connectivity -n ai-nutritionist --image=curlimages/curl:latest --rm -it --restart=Never -- /bin/sh

# Inside the test pod:
curl nutrition-service.ai-nutritionist.svc.cluster.local:8080/health
curl ai-coach-service.ai-nutritionist.svc.cluster.local:8080/health
curl messaging-service.ai-nutritionist.svc.cluster.local:8080/health
```

### Load Testing

Traffic isolation for load testing:

```bash
curl -H "x-load-test: true" -H "x-test-scenario: stress" api.ai-nutritionist.com/api/v1/nutrition
```

### Circuit Breaker Testing

```bash
curl -H "x-circuit-breaker-test: enabled" api.ai-nutritionist.com/api/v1/ai-coach
```

## 🔍 Monitoring & Debugging

### Service Mesh Status

```bash
# Overall mesh status
istioctl proxy-status

# Configuration for specific pod
istioctl proxy-config cluster <pod-name> -n ai-nutritionist

# Envoy admin interface
kubectl port-forward <pod-name> 15000:15000 -n ai-nutritionist
# Access: http://localhost:15000
```

### Access Observability Tools

```bash
# Grafana dashboards
kubectl port-forward -n istio-system svc/grafana 3000:3000

# Jaeger tracing
kubectl port-forward -n istio-system svc/jaeger 16686:16686

# Kiali service graph
kubectl port-forward -n istio-system svc/kiali 20001:20001

# Prometheus metrics
kubectl port-forward -n istio-system svc/prometheus 9090:9090
```

### Debugging Commands

```bash
# Check gateway configuration
kubectl get gateway -n ai-nutritionist -o yaml

# Check virtual service routing
kubectl get virtualservice -n ai-nutritionist -o yaml

# Check destination rules
kubectl get destinationrule -n ai-nutritionist -o yaml

# Check security policies
kubectl get peerauthentication,authorizationpolicy -n ai-nutritionist

# View Envoy configuration
istioctl proxy-config route <pod-name> -n ai-nutritionist
istioctl proxy-config cluster <pod-name> -n ai-nutritionist
istioctl proxy-config listener <pod-name> -n ai-nutritionist
```

## 🔐 Security Best Practices

### Certificate Management

```bash
# Check certificate status
kubectl get secret ai-nutritionist-tls -n ai-nutritionist

# Renew certificates (if using cert-manager)
kubectl annotate secret ai-nutritionist-tls -n ai-nutritionist cert-manager.io/issue-temporary-certificate=""
```

### Security Validation

```bash
# Test mTLS connectivity
istioctl authn tls-check <pod-name>.<namespace>.svc.cluster.local

# Validate authorization policies
istioctl proxy-config rbac <pod-name> -n ai-nutritionist
```

## 📊 Performance Optimization

### Resource Tuning

**Istio Components:**

- Pilot: 2-10 replicas based on load
- Gateway: 3-20 replicas with HPA
- Proxy sidecar: 100m-2000m CPU, 128Mi-1Gi memory

**Application Services:**

- Connection pool sizes tuned per service
- Circuit breaker thresholds optimized for SLA
- Retry policies balanced for resilience vs latency

### Scaling Guidelines

**Horizontal Pod Autoscaling:**

- CPU target: 70-80%
- Memory target: 80%
- Custom metrics: Request rate, queue depth

**Cluster Autoscaling:**

- Node groups for different workload types
- Spot instances for non-critical workloads
- Reserved instances for stable workloads

## 🛠️ Troubleshooting

### Common Issues

1. **503 Service Unavailable**

   - Check destination rule subsets
   - Verify service labels match selectors
   - Check circuit breaker status

2. **mTLS Connection Issues**

   - Verify PeerAuthentication policies
   - Check certificate validity
   - Ensure sidecar injection

3. **High Latency**

   - Check retry policies
   - Examine connection pool settings
   - Review circuit breaker configuration

4. **Authorization Denied**
   - Verify JWT token validity
   - Check authorization policy rules
   - Ensure proper header propagation

### Emergency Procedures

**Disable Security (Emergency Only):**

```bash
kubectl patch peerauthentication default -n ai-nutritionist --type='merge' -p='{"spec":{"mtls":{"mode":"PERMISSIVE"}}}'
```

**Emergency Traffic Bypass:**

```bash
kubectl patch virtualservice ai-nutritionist-traffic-management -n ai-nutritionist --type='json' -p='[{"op":"replace","path":"/spec/http/0/fault","value":null}]'
```

## 📈 Metrics & KPIs

### SLIs (Service Level Indicators)

- **Availability**: > 99.9%
- **Latency**: P99 < 2000ms
- **Error Rate**: < 0.1%
- **Throughput**: > 1000 RPS

### Business Metrics

- **User Satisfaction**: Based on latency and errors
- **Feature Adoption**: A/B test conversion rates
- **Revenue Impact**: Premium feature usage
- **Cost Optimization**: Resource utilization

## 🔄 Deployment Strategies

### Rollout Procedures

1. **Canary Deployment**

   - Deploy to canary subset
   - Route 5% traffic gradually
   - Monitor error rates and latency
   - Full rollout or rollback based on metrics

2. **Blue-Green Deployment**

   - Deploy to green environment
   - Test in isolation
   - Switch traffic instantly
   - Keep blue as fallback

3. **Feature Flag Rollout**
   - Deploy with feature disabled
   - Enable for test users
   - Gradual rollout to all users
   - Monitor business metrics

### Rollback Procedures

```bash
# Quick rollback (change traffic weights)
kubectl patch virtualservice nutrition-service-canary -n ai-nutritionist --type='json' -p='[{"op":"replace","path":"/spec/http/0/route/0/weight","value":100},{"op":"replace","path":"/spec/http/0/route/1/weight","value":0}]'

# Full rollback (revert deployment)
kubectl rollout undo deployment/nutrition-service -n ai-nutritionist
```

## 📚 Additional Resources

- [Istio Documentation](https://istio.io/latest/docs/)
- [Envoy Proxy Documentation](https://www.envoyproxy.io/docs/)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Jaeger Tracing](https://www.jaegertracing.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)

## 🆘 Support

For issues or questions:

1. Check the troubleshooting section
2. Review Istio logs: `kubectl logs -n istio-system deployment/istiod`
3. Examine service mesh status: `istioctl proxy-status`
4. Contact the platform team with specific error messages and configurations
