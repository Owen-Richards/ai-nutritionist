# Monitoring & Analytics Usage Guide

This guide explains how to access the integrated monitoring and analytics features that replace the removed standalone scripts.

## Overview

The AI Nutritionist application has comprehensive built-in monitoring and cost optimization features. These integrated solutions provide more functionality and better reliability than standalone scripts.

## Cost Optimization & Monitoring

### Real-Time Dashboard Access

```python
from src.services.infrastructure.dashboard import ImprovementDashboard
from src.services.infrastructure.monitoring import PerformanceMonitoringService

# Initialize services
dashboard = ImprovementDashboard()
monitoring = PerformanceMonitoringService()

# Get real-time system health
health_status = dashboard.get_real_time_health_check()
print(f"System Status: {health_status['system_status']}")
print(f"Uptime: {health_status['uptime_percentage']}%")

# Get performance metrics
performance = monitoring.get_performance_dashboard()
print(f"Response Time: {performance['performance']['avg_response_time']}ms")
print(f"Throughput: {performance['performance']['requests_per_second']}")

# Generate comprehensive improvement report
report = dashboard.generate_improvement_report(days=30)
print(f"Cost Savings: {report['detailed_metrics']['cost_optimization']['total_savings']}")
```

### Cost Analysis & Optimization

```python
from src.services.business.cost_tracking import UserCostTracker
from src.services.business.cost_optimizer import IntelligentCostOptimizer

# Initialize cost services
cost_tracker = UserCostTracker()
optimizer = IntelligentCostOptimizer()

# Analyze user costs
user_phone = "+1234567890"
monthly_summary = cost_tracker.get_user_monthly_summary(user_phone)
print(f"Monthly Cost: ${monthly_summary['total_cost']:.4f}")
print(f"Usage Count: {monthly_summary['total_usage']}")

# Get optimization recommendations
recommendations = optimizer.get_cost_optimization_recommendations()
for rec in recommendations:
    print(f"- {rec['description']}")
    print(f"  Potential Savings: ${rec.get('estimated_savings', 0):.2f}")
```

## Usage Reporting & Analytics

### Messaging Usage Analysis

```python
from src.services.infrastructure.monitoring import PerformanceMonitoringService
from src.services.analytics.warehouse_processor import WarehouseProcessor

# Get comprehensive analytics
monitoring = PerformanceMonitoringService()
warehouse = WarehouseProcessor()

# Get user analytics
user_analytics = monitoring.get_user_analytics("+1234567890", days=7)
print(f"Total Interactions: {user_analytics['total_interactions']}")
print(f"Engagement Score: {user_analytics['engagement_score']}")

# Get dashboard data
dashboard_data = await warehouse.get_dashboard_data()
print(f"Total Events: {dashboard_data['overview']['total_events']}")
print(f"Active Users: {dashboard_data['overview']['total_users']}")
```

### API Usage Tracking

```python
from src.services.nutrition.calculator import EdamamUsageTracker

# Track API usage and costs
usage_tracker = EdamamUsageTracker()

# Get daily usage summary
daily_summary = await usage_tracker.get_daily_usage_summary()
print(f"Daily API Calls: {daily_summary['total_calls']}")
print(f"Daily Cost: ${daily_summary['total_cost']:.4f}")

# Check budget alerts
monthly_budget = 50.0  # $50/month
alerts = await usage_tracker.check_budget_alerts(monthly_budget)
for alert in alerts:
    print(f"⚠️ {alert}")
```

## API Endpoints

When the application is running, you can access monitoring data via HTTP endpoints:

### Dashboard Endpoints

- `GET /v1/dashboard/system-health` - Real-time system health
- `GET /v1/dashboard/performance` - Performance metrics
- `GET /v1/dashboard/cost-analysis` - Cost optimization dashboard

### Analytics Endpoints

- `GET /v1/analytics/summary` - Executive dashboard
- `GET /v1/analytics/user-journey/{user_id}` - User behavior analysis
- `GET /v1/analytics/revenue` - Revenue metrics

### Example API Usage

```bash
# Get system health (when API is running)
curl http://localhost:3000/v1/dashboard/system-health

# Get performance metrics
curl http://localhost:3000/v1/dashboard/performance

# Get user analytics
curl http://localhost:3000/v1/analytics/user-journey/+1234567890
```

## Running the Application

```bash
# Start the API locally
sam local start-api

# Or run with SAM build/deploy
sam build
sam deploy --guided

# Run tests to validate monitoring
python -m pytest tests/unit/test_gamification.py::TestPerformance -v
```

## Configuration

Cost optimization and monitoring settings can be adjusted in:

- `src/config/cost_optimization_config.py` - Cost limits and thresholds
- `src/config/settings.py` - General application settings
- `src/services/infrastructure/monitoring.py` - Monitoring thresholds

## Advantages Over Standalone Scripts

1. **Integration** - Direct access to application state and data
2. **Real-time** - Live monitoring without separate processes
3. **Reliability** - Uses the same error handling as main application
4. **Performance** - No additional AWS API calls or database connections
5. **Maintenance** - Single codebase with consistent patterns
6. **Testing** - Covered by existing test suite

## Migration Notes

If you were previously using the standalone scripts:

- **`messaging_usage_report.py`** → Use `PerformanceMonitoringService.get_user_analytics()`
- **`cost_optimization_cli.py`** → Use `ImprovementDashboard` and `CostOptimizationService`

The integrated solutions provide all the same functionality with better performance and reliability.
