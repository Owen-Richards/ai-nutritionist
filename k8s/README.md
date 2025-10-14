# AI Nutritionist Kubernetes Configuration

This directory contains comprehensive Kubernetes configurations for deploying the AI Nutritionist platform with enterprise-grade features including service mesh, monitoring, autoscaling, and security policies.

## 🏗️ Architecture Overview

The Kubernetes deployment includes:

- **Microservices**: Nutrition Service, AI Coach Service, Health Tracking, Messaging, Payment
- **Frontend Applications**: Web App, Mobile API, Bot Services (WhatsApp, SMS, iMessage)
- **Infrastructure**: Redis cache, DynamoDB Local (for development)
- **Service Mesh**: Istio for traffic management, security, and observability
- **Monitoring**: Prometheus, Grafana, Jaeger for comprehensive observability
- **Autoscaling**: HPA, VPA, and Cluster Autoscaling
- **Security**: Network policies, pod security policies, RBAC

## 📁 Directory Structure

```
k8s/
├── base/                          # Base Kubernetes configurations
│   ├── kustomization.yaml         # Main Kustomization file
│   ├── namespace.yaml             # Namespace definition
│   ├── configmaps.yaml            # Application configuration
│   ├── secrets.yaml               # Secrets templates
│   ├── rbac.yaml                  # RBAC configuration
│   ├── ingress.yaml               # Ingress and network policies
│   ├── scaling-policies.yaml      # VPA, Resource quotas, PDB
│   ├── nutrition-service/         # Nutrition service manifests
│   ├── ai-coach-service/          # AI Coach service manifests
│   ├── health-tracking-service/   # Health tracking manifests
│   ├── messaging-service/         # Messaging service manifests
│   ├── payment-service/           # Payment service manifests
│   ├── web-app/                   # Web application manifests
│   └── redis/                     # Redis StatefulSet
├── overlays/                      # Environment-specific configurations
│   ├── development/               # Development environment
│   ├── staging/                   # Staging environment
│   └── production/                # Production environment
├── monitoring/                    # Monitoring stack
│   ├── prometheus-grafana.yaml    # Prometheus and Grafana
│   └── jaeger.yaml               # Jaeger tracing
├── istio/                        # Service mesh configuration
│   ├── istio-config.yaml         # Istio installation and gateways
│   └── security-policies.yaml    # mTLS and authorization policies
├── security/                     # Security policies
│   └── pod-security-policies.yaml # PSP and network policies
├── deploy.sh                     # Deployment script
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster**: EKS, GKE, AKS, or local (minikube/kind)
2. **kubectl**: Kubernetes CLI tool
3. **kustomize**: Configuration management tool
4. **istioctl**: Istio CLI (optional, for service mesh)

### Basic Deployment

1. **Development Environment**:

```bash
# Deploy to development
./deploy.sh -e development

# Deploy with monitoring
./deploy.sh -e development -m

# Deploy with Istio service mesh
./deploy.sh -e development -i -m
```

2. **Production Environment**:

```bash
# Deploy to production with all features
./deploy.sh -e production -i -m

# Dry run to preview changes
./deploy.sh -e production -i -m --dry-run
```

### Manual Deployment

If you prefer manual deployment:

```bash
# Create namespace
kubectl create namespace ai-nutritionist

# Deploy base configuration
kustomize build overlays/development | kubectl apply -f -

# Or for production
kustomize build overlays/production | kubectl apply -f -
```

## 🔧 Configuration

### Environment Variables

Key configuration is managed through ConfigMaps and Secrets:

- **ConfigMaps**: Application settings, service URLs, feature flags
- **Secrets**: API keys, database passwords, certificates

### Resource Management

- **Requests/Limits**: CPU and memory resources defined per service
- **HPA**: Horizontal Pod Autoscaler based on CPU, memory, and custom metrics
- **VPA**: Vertical Pod Autoscaler for automatic resource optimization
- **PDB**: Pod Disruption Budgets for high availability

### Scaling Configuration

1. **Horizontal Pod Autoscaler (HPA)**:

   - CPU-based: Scale at 70% CPU utilization
   - Memory-based: Scale at 80% memory utilization
   - Custom metrics: Requests per second, AI model latency

2. **Vertical Pod Autoscaler (VPA)**:

   - Automatic resource recommendations
   - Update mode: Auto for development, Off for production

3. **Cluster Autoscaler**:
   - Automatic node scaling based on resource requests
   - Node pools for different workload types (AI, general)

## 📊 Monitoring and Observability

### Prometheus Metrics

The platform exposes comprehensive metrics:

- **Application Metrics**: Request rate, response time, error rate
- **Business Metrics**: AI model usage, nutrition plans created, user engagement
- **Infrastructure Metrics**: CPU, memory, disk, network

### Grafana Dashboards

Pre-configured dashboards for:

- Application performance overview
- Service-specific metrics
- Infrastructure monitoring
- Business KPIs

### Distributed Tracing (Jaeger)

- Request tracing across microservices
- AI model performance tracking
- Database query optimization
- External API call monitoring

### Log Aggregation

- Structured logging with JSON format
- Log correlation with trace IDs
- Centralized logging with ELK stack (optional)

## 🔒 Security

### Network Security

1. **Network Policies**: Restrict pod-to-pod communication
2. **Istio Security**: mTLS encryption between services
3. **Ingress Security**: TLS termination, rate limiting

### Pod Security

1. **Pod Security Policies**: Enforce security constraints
2. **Security Contexts**: Non-root users, read-only filesystems
3. **Resource Limits**: Prevent resource exhaustion attacks

### RBAC (Role-Based Access Control)

- Service accounts with minimal required permissions
- Separate roles for different service types
- Monitoring-specific access controls

### Secrets Management

- Kubernetes secrets for sensitive data
- AWS IAM roles for cloud service access
- External secret management integration support

## 🌐 Service Mesh (Istio)

### Traffic Management

- **Virtual Services**: Routing rules and traffic splitting
- **Destination Rules**: Load balancing and circuit breaking
- **Gateways**: Ingress and egress traffic control

### Security Policies

- **mTLS**: Automatic mutual TLS between services
- **Authorization Policies**: Fine-grained access control
- **Security Policies**: JWT validation, RBAC

### Observability

- **Automatic Metrics**: Request metrics without code changes
- **Distributed Tracing**: Request flow visualization
- **Access Logs**: Detailed request logging

## 🔄 CI/CD Integration

### GitOps Workflow

1. **Development**:

   - Deploy from feature branches
   - Automatic testing and validation
   - Preview environments

2. **Staging**:

   - Production-like environment
   - Full integration testing
   - Performance validation

3. **Production**:
   - Blue-green deployments
   - Gradual rollouts with Istio
   - Automatic rollback on errors

### Image Management

- **Development**: `dev-latest` tags for rapid iteration
- **Staging**: Semantic versioning with release candidates
- **Production**: Immutable tags with security scanning

## 📈 Performance Optimization

### AI Workload Optimization

- **Node Affinity**: Schedule AI services on GPU nodes
- **Resource Allocation**: Appropriate CPU/memory for AI models
- **Caching Strategy**: Multi-layer caching for AI responses

### Database Optimization

- **Connection Pooling**: Efficient database connections
- **Read Replicas**: Scale read operations
- **Caching**: Redis for frequently accessed data

### Cost Optimization

- **Resource Right-sizing**: VPA recommendations
- **Spot Instances**: Cost-effective compute for non-critical workloads
- **Cluster Autoscaling**: Scale down during low usage periods

## 🚨 Troubleshooting

### Common Issues

1. **Pod Startup Issues**:

```bash
# Check pod status
kubectl get pods -n ai-nutritionist

# View pod logs
kubectl logs <pod-name> -n ai-nutritionist

# Describe pod for events
kubectl describe pod <pod-name> -n ai-nutritionist
```

2. **Service Connectivity**:

```bash
# Test service connectivity
kubectl exec -it <pod-name> -n ai-nutritionist -- curl http://service-name:port/health

# Check service endpoints
kubectl get endpoints -n ai-nutritionist
```

3. **Resource Issues**:

```bash
# Check resource usage
kubectl top pods -n ai-nutritionist
kubectl top nodes

# Check HPA status
kubectl get hpa -n ai-nutritionist
```

### Monitoring Health

1. **Application Health**:

   - Health check endpoints: `/health`, `/ready`
   - Prometheus metrics: `up`, `http_requests_total`
   - Grafana alerts for service unavailability

2. **Infrastructure Health**:
   - Node resource utilization
   - Persistent volume status
   - Network connectivity

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Istio Documentation](https://istio.io/latest/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AI Nutritionist Architecture Guide](../docs/architecture.md)

## 🤝 Contributing

1. Follow the GitOps workflow for changes
2. Test changes in development environment first
3. Update documentation for configuration changes
4. Use semantic versioning for image tags

## 📞 Support

For issues and questions:

- Create GitHub issues for bugs and feature requests
- Use monitoring alerts for operational issues
- Check logs and metrics for troubleshooting
