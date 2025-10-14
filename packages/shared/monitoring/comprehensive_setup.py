"""
Comprehensive Performance Monitoring Setup

Sets up all monitoring components including performance monitoring, business metrics,
infrastructure monitoring, distributed tracing, dashboards, and alerts.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .performance_monitor import setup_performance_monitoring, get_performance_monitor
from .business_metrics import setup_business_tracking, get_business_tracker
from .infrastructure_monitor import setup_infrastructure_monitoring, get_infrastructure_monitor
from .distributed_tracing import setup_distributed_tracing, get_distributed_tracer
from .dashboards import setup_dashboard_management, get_dashboard_manager
from .alerts import setup_alert_management, get_alert_manager

logger = logging.getLogger(__name__)


class ComprehensiveMonitoringSetup:
    """
    Sets up and manages all monitoring components
    """
    
    def __init__(
        self,
        service_name: str = "ai-nutritionist",
        region: str = "us-east-1",
        enable_xray: bool = True,
        sns_topic_arn: Optional[str] = None
    ):
        self.service_name = service_name
        self.region = region
        self.enable_xray = enable_xray
        self.sns_topic_arn = sns_topic_arn
        
        # Monitoring components
        self.performance_monitor = None
        self.business_tracker = None
        self.infrastructure_monitor = None
        self.distributed_tracer = None
        self.dashboard_manager = None
        self.alert_manager = None
        
        # Setup status
        self.setup_complete = False
        self.component_status = {}
    
    async def setup_all_monitoring(self) -> Dict[str, Any]:
        """Setup all monitoring components"""
        logger.info(f"Setting up comprehensive monitoring for {self.service_name}")
        
        setup_results = {
            'service': self.service_name,
            'region': self.region,
            'setup_timestamp': datetime.utcnow().isoformat(),
            'components': {},
            'dashboards': {},
            'alerts': {},
            'errors': []
        }
        
        try:
            # 1. Setup Performance Monitoring
            logger.info("Setting up performance monitoring...")
            self.performance_monitor = setup_performance_monitoring(
                service_name=self.service_name,
                region=self.region,
                enable_xray=self.enable_xray
            )
            setup_results['components']['performance_monitor'] = 'success'
            self.component_status['performance_monitor'] = True
            
        except Exception as e:
            logger.error(f"Failed to setup performance monitoring: {e}")
            setup_results['components']['performance_monitor'] = f'error: {str(e)}'
            setup_results['errors'].append(f"Performance monitoring: {str(e)}")
            self.component_status['performance_monitor'] = False
        
        try:
            # 2. Setup Business Metrics Tracking
            logger.info("Setting up business metrics tracking...")
            self.business_tracker = setup_business_tracking(
                region=self.region
            )
            setup_results['components']['business_tracker'] = 'success'
            self.component_status['business_tracker'] = True
            
        except Exception as e:
            logger.error(f"Failed to setup business tracking: {e}")
            setup_results['components']['business_tracker'] = f'error: {str(e)}'
            setup_results['errors'].append(f"Business tracking: {str(e)}")
            self.component_status['business_tracker'] = False
        
        try:
            # 3. Setup Infrastructure Monitoring
            logger.info("Setting up infrastructure monitoring...")
            self.infrastructure_monitor = setup_infrastructure_monitoring(
                service_name=self.service_name,
                region=self.region
            )
            setup_results['components']['infrastructure_monitor'] = 'success'
            self.component_status['infrastructure_monitor'] = True
            
        except Exception as e:
            logger.error(f"Failed to setup infrastructure monitoring: {e}")
            setup_results['components']['infrastructure_monitor'] = f'error: {str(e)}'
            setup_results['errors'].append(f"Infrastructure monitoring: {str(e)}")
            self.component_status['infrastructure_monitor'] = False
        
        try:
            # 4. Setup Distributed Tracing
            logger.info("Setting up distributed tracing...")
            self.distributed_tracer = setup_distributed_tracing(
                service_name=self.service_name,
                region=self.region,
                enable_xray=self.enable_xray
            )
            setup_results['components']['distributed_tracer'] = 'success'
            self.component_status['distributed_tracer'] = True
            
        except Exception as e:
            logger.error(f"Failed to setup distributed tracing: {e}")
            setup_results['components']['distributed_tracer'] = f'error: {str(e)}'
            setup_results['errors'].append(f"Distributed tracing: {str(e)}")
            self.component_status['distributed_tracer'] = False
        
        try:
            # 5. Setup Dashboard Management
            logger.info("Setting up dashboard management...")
            self.dashboard_manager = setup_dashboard_management(
                service_name=self.service_name,
                region=self.region
            )
            
            # Create all dashboards
            dashboard_urls = await self.dashboard_manager.create_all_dashboards()
            setup_results['dashboards'] = dashboard_urls
            setup_results['components']['dashboard_manager'] = 'success'
            self.component_status['dashboard_manager'] = True
            
        except Exception as e:
            logger.error(f"Failed to setup dashboard management: {e}")
            setup_results['components']['dashboard_manager'] = f'error: {str(e)}'
            setup_results['errors'].append(f"Dashboard management: {str(e)}")
            self.component_status['dashboard_manager'] = False
        
        try:
            # 6. Setup Alert Management
            logger.info("Setting up alert management...")
            self.alert_manager = setup_alert_management(
                service_name=self.service_name,
                region=self.region,
                sns_topic_arn=self.sns_topic_arn
            )
            
            # Create all alerts
            alert_arns = await self.alert_manager.setup_all_alerts()
            setup_results['alerts'] = alert_arns
            setup_results['components']['alert_manager'] = 'success'
            self.component_status['alert_manager'] = True
            
        except Exception as e:
            logger.error(f"Failed to setup alert management: {e}")
            setup_results['components']['alert_manager'] = f'error: {str(e)}'
            setup_results['errors'].append(f"Alert management: {str(e)}")
            self.component_status['alert_manager'] = False
        
        # Mark setup as complete if at least core components are working
        core_components = ['performance_monitor', 'infrastructure_monitor']
        self.setup_complete = all(
            self.component_status.get(comp, False) 
            for comp in core_components
        )
        
        setup_results['setup_complete'] = self.setup_complete
        setup_results['component_status'] = self.component_status
        
        if self.setup_complete:
            logger.info("Comprehensive monitoring setup completed successfully!")
        else:
            logger.warning("Monitoring setup completed with some errors. Check component status.")
        
        return setup_results
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status"""
        status = {
            'service': self.service_name,
            'timestamp': datetime.utcnow().isoformat(),
            'setup_complete': self.setup_complete,
            'component_status': self.component_status,
            'metrics_summary': {}
        }
        
        # Get metrics from each component
        try:
            if self.performance_monitor:
                status['metrics_summary']['performance'] = self.performance_monitor.get_performance_summary()
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            status['metrics_summary']['performance'] = {'error': str(e)}
        
        try:
            if self.business_tracker:
                status['metrics_summary']['business'] = self.business_tracker.get_business_summary()
        except Exception as e:
            logger.error(f"Error getting business summary: {e}")
            status['metrics_summary']['business'] = {'error': str(e)}
        
        try:
            if self.infrastructure_monitor:
                status['metrics_summary']['infrastructure'] = self.infrastructure_monitor.get_infrastructure_summary()
        except Exception as e:
            logger.error(f"Error getting infrastructure summary: {e}")
            status['metrics_summary']['infrastructure'] = {'error': str(e)}
        
        try:
            if self.distributed_tracer:
                status['metrics_summary']['tracing'] = self.distributed_tracer.get_trace_summary()
        except Exception as e:
            logger.error(f"Error getting trace summary: {e}")
            status['metrics_summary']['tracing'] = {'error': str(e)}
        
        try:
            if self.alert_manager:
                status['metrics_summary']['alerts'] = self.alert_manager.get_alert_summary()
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            status['metrics_summary']['alerts'] = {'error': str(e)}
        
        try:
            if self.dashboard_manager:
                status['dashboards'] = self.dashboard_manager.get_dashboard_summary()
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            status['dashboards'] = {'error': str(e)}
        
        return status


# Global monitoring setup instance
_monitoring_setup: Optional[ComprehensiveMonitoringSetup] = None


async def setup_comprehensive_monitoring(
    service_name: str = "ai-nutritionist",
    region: str = "us-east-1",
    enable_xray: bool = True,
    sns_topic_arn: Optional[str] = None
) -> ComprehensiveMonitoringSetup:
    """Setup comprehensive monitoring for the service"""
    global _monitoring_setup
    
    _monitoring_setup = ComprehensiveMonitoringSetup(
        service_name=service_name,
        region=region,
        enable_xray=enable_xray,
        sns_topic_arn=sns_topic_arn
    )
    
    setup_results = await _monitoring_setup.setup_all_monitoring()
    
    # Log setup summary
    logger.info(f"Monitoring setup results:")
    logger.info(f"- Service: {setup_results['service']}")
    logger.info(f"- Setup Complete: {setup_results['setup_complete']}")
    logger.info(f"- Components: {len([k for k, v in setup_results['components'].items() if v == 'success'])}/{len(setup_results['components'])}")
    logger.info(f"- Dashboards: {len(setup_results.get('dashboards', {}))}")
    logger.info(f"- Alerts: {len(setup_results.get('alerts', {}))}")
    
    if setup_results['errors']:
        logger.warning(f"Setup errors: {setup_results['errors']}")
    
    return _monitoring_setup


def get_monitoring_setup() -> Optional[ComprehensiveMonitoringSetup]:
    """Get the global monitoring setup instance"""
    return _monitoring_setup


async def get_comprehensive_status() -> Dict[str, Any]:
    """Get comprehensive monitoring status"""
    if _monitoring_setup:
        return await _monitoring_setup.get_monitoring_status()
    else:
        return {
            'error': 'Monitoring not initialized',
            'suggestion': 'Call setup_comprehensive_monitoring() first'
        }
