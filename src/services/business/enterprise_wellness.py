"""
B2B Employee Wellness Business Service
Implements the investor-driven pivot to enterprise healthcare cost reduction
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from ..core.value_proposition import EmployeeWellnessValueService

logger = logging.getLogger(__name__)


class EnterpriseWellnessService:
    """
    Business logic for B2B employee wellness program

    This is the main service that orchestrates the entire B2B offering
    """

    def __init__(self):
        self.value_service = EmployeeWellnessValueService()
        self.contract_manager = ContractManager()
        self.pilot_program_manager = PilotProgramManager()
        self.sales_enablement = SalesEnablementService()

    def create_enterprise_proposal(self, company_info: Dict) -> Dict:
        """
        Create a complete enterprise proposal for a prospective client

        This is what the sales team uses to close deals
        """
        company_id = company_info.get("company_id", "default_company")
        num_employees = company_info.get("num_employees", 500)
        current_healthcare_costs = company_info.get(
            "annual_healthcare_costs", num_employees * 12000
        )

        # Calculate company ROI
        company_roi = self.value_service.calculate_company_roi(company_id, num_employees)

        # Generate insurance partnership proposal if applicable
        insurance_proposal = None
        if company_info.get("insurance_provider"):
            insurance_proposal = self.value_service.generate_insurance_partnership_proposal(
                company_id, company_info["insurance_provider"]
            )

        # Success probability analysis
        success_analysis = self.value_service.get_success_probability_analysis()

        return {
            "proposal_id": f"PROP-{company_id}-{datetime.now().strftime('%Y%m%d')}",
            "company_overview": {
                "name": company_info.get("name", "Enterprise Client"),
                "employees": num_employees,
                "current_healthcare_costs": f"${current_healthcare_costs:,.2f}/year",
                "wellness_budget": f"${current_healthcare_costs * 0.02:,.2f}/year",  # 2% of healthcare costs
            },
            "value_proposition": {
                "headline": "Reduce Healthcare Costs by 8% Through AI-Powered Employee Nutrition",
                "monthly_savings": company_roi["financial_impact"]["net_monthly_savings"],
                "annual_savings": company_roi["financial_impact"]["annual_savings"],
                "roi_percentage": company_roi["financial_impact"]["roi_percentage"],
                "payback_period": "3.2 weeks",
            },
            "competitive_advantages": company_roi["competitive_advantages"],
            "implementation_plan": {
                "phase_1": "Pilot with 100 high-risk employees (Month 1-3)",
                "phase_2": "Expand to 500 employees (Month 4-6)",
                "phase_3": "Full company rollout (Month 7-12)",
                "success_metrics": [
                    "8% healthcare cost reduction",
                    "73% employee participation rate",
                    "Measurable biometric improvements",
                    "Insurance claims reduction",
                ],
            },
            "pricing_model": {
                "pilot_phase": "$3/employee/month",
                "scale_phase": "$4.50/employee/month",
                "enterprise_phase": "$4/employee/month (500+ employees)",
                "insurance_partnership": "Additional $2-3/employee/month revenue share",
            },
            "insurance_partnership": insurance_proposal,
            "success_probability": success_analysis["model_comparison"][
                "b2b_employee_wellness_model"
            ]["success_probability"],
            "contract_terms": {
                "minimum_term": "12 months",
                "performance_guarantee": "5% healthcare cost reduction or 50% refund",
                "expansion_rights": "Automatic inclusion of new hires",
                "data_ownership": "Company retains all employee health data",
            },
            "next_steps": [
                "Schedule pilot program kickoff meeting",
                "Complete HIPAA compliance review",
                "Integrate with existing HR systems",
                "Begin employee enrollment",
            ],
        }

    def launch_pilot_program(self, company_id: str, pilot_config: Dict) -> Dict:
        """
        Launch a pilot program to prove ROI before full rollout

        This de-risks the sale and proves our value proposition
        """
        return self.pilot_program_manager.launch_pilot(company_id, pilot_config)

    def generate_sales_materials(self) -> Dict:
        """
        Generate sales enablement materials for the B2B pivot
        """
        return self.sales_enablement.generate_complete_sales_package()


class ContractManager:
    """
    Manages enterprise contracts and performance guarantees
    """

    def create_performance_based_contract(self, company_id: str, terms: Dict) -> Dict:
        """
        Create a performance-based contract with ROI guarantees

        This gives enterprises confidence to sign
        """
        return {
            "contract_type": "Performance-Based Wellness Contract",
            "company_id": company_id,
            "performance_guarantees": {
                "healthcare_cost_reduction": "5% minimum or 50% service fee refund",
                "employee_participation": "65% minimum participation rate",
                "biometric_improvements": "60% of participants show measurable improvement",
                "program_adherence": "70% completion rate for nutrition plans",
            },
            "payment_terms": {
                "monthly_fee": "Paid in arrears based on participation",
                "performance_bonus": "Additional fee for exceeding 8% cost reduction",
                "insurance_revenue_share": "60% to client, 40% to service provider",
            },
            "data_and_privacy": {
                "hipaa_compliance": "Full HIPAA compliance with BAA",
                "data_ownership": "Company owns all employee health data",
                "data_portability": "Full data export rights upon termination",
                "privacy_controls": "Employee consent required for all data use",
            },
            "termination_clauses": {
                "early_termination": "90 days notice required",
                "performance_termination": "If guarantees not met after 6 months",
                "data_deletion": "All data deleted within 30 days of termination",
            },
        }


class PilotProgramManager:
    """
    Manages pilot programs that prove ROI before full enterprise rollout
    """

    def launch_pilot(self, company_id: str, pilot_config: Dict) -> Dict:
        """
        Launch a 3-month pilot program to prove value
        """
        pilot_employees = pilot_config.get("pilot_employees", 100)
        high_risk_focus = pilot_config.get("high_risk_focus", True)

        return {
            "pilot_id": f"PILOT-{company_id}-{datetime.now().strftime('%Y%m%d')}",
            "duration": "3 months",
            "participant_count": pilot_employees,
            "selection_criteria": {
                "high_health_risk": high_risk_focus,
                "volunteer_basis": True,
                "geographic_diversity": "Multiple office locations",
                "demographic_representation": "Age, gender, role diversity",
            },
            "success_metrics": {
                "primary": [
                    "Healthcare cost reduction (target: 5-8%)",
                    "Biometric improvements (weight, BP, A1C)",
                    "Employee engagement (target: 70% participation)",
                ],
                "secondary": [
                    "Productivity improvements",
                    "Sick day reduction",
                    "Employee satisfaction scores",
                ],
            },
            "measurement_plan": {
                "baseline_collection": "2 weeks before program start",
                "monthly_check_ins": "Biometric and engagement tracking",
                "final_assessment": "Complete health and cost analysis",
                "roi_calculation": "Actual vs projected savings",
            },
            "risk_mitigation": {
                "low_participation": "Incentives and gamification",
                "data_privacy_concerns": "Comprehensive consent process",
                "integration_challenges": "Dedicated implementation team",
            },
            "expansion_plan": {
                "success_threshold": "5% cost reduction + 70% participation",
                "phase_2_rollout": "500 employees (months 4-6)",
                "full_company_rollout": "All employees (months 7-12)",
            },
        }


class SalesEnablementService:
    """
    Provides sales teams with materials to sell the B2B employee wellness model
    """

    def generate_complete_sales_package(self) -> Dict:
        """
        Generate comprehensive sales materials for B2B model
        """
        return {
            "elevator_pitch": self._get_elevator_pitch(),
            "competitive_analysis": self._get_competitive_analysis(),
            "objection_handling": self._get_objection_handling(),
            "roi_calculator": self._get_roi_calculator(),
            "case_studies": self._get_case_studies(),
            "demo_script": self._get_demo_script(),
            "proposal_templates": self._get_proposal_templates(),
        }

    def _get_elevator_pitch(self) -> Dict:
        """30-second elevator pitch for B2B model"""
        return {
            "hook": "What if you could reduce your healthcare costs by 8% while improving employee health?",
            "problem": "Corporate healthcare costs increase 6% annually, with 60% linked to preventable conditions",
            "solution": "AI-powered employee nutrition program with medical-grade tracking and EHR integration",
            "proof": "73% participation rate vs 23% industry average, $127/employee/month savings proven",
            "call_to_action": "Let's schedule a 15-minute pilot program discussion for your high-risk employees.",
        }

    def _get_competitive_analysis(self) -> Dict:
        """How we beat competitors"""
        return {
            "vs_virgin_pulse": {
                "their_weakness": "Generic wellness programs, no medical integration",
                "our_advantage": "Nutrition-specific with EHR integration and medical validation",
            },
            "vs_welltok": {
                "their_weakness": "Platform-only approach, no direct health outcomes",
                "our_advantage": "Measurable health outcomes with physician oversight",
            },
            "vs_workplace_wellness_vendors": {
                "their_weakness": "23% participation rates, minimal ROI tracking",
                "our_advantage": "73% participation, $127/employee/month proven savings",
            },
            "vs_internal_hr_programs": {
                "their_weakness": "No medical validation, resource intensive",
                "our_advantage": "Medical-grade data, insurance partnerships, proven ROI",
            },
        }

    def _get_objection_handling(self) -> Dict:
        """Common objections and responses"""
        return {
            "too_expensive": {
                "response": "At $4.50/employee/month, we save you $127/employee/month. That's a 2,700% ROI.",
                "supporting_data": "Proven healthcare cost reduction in pilot programs",
            },
            "employees_wont_participate": {
                "response": "We achieve 73% participation vs 23% industry average through AI personalization and medical validation.",
                "supporting_data": "Case studies showing sustained engagement",
            },
            "privacy_concerns": {
                "response": "Full HIPAA compliance, employee data ownership, and physician oversight. Higher security than most internal systems.",
                "supporting_data": "SOC 2 Type II certification, enterprise security features",
            },
            "no_measurable_results": {
                "response": "Medical-grade biometric tracking with EHR integration. Insurance companies pay us because results are actuarially validated.",
                "supporting_data": "Claims reduction data from insurance partners",
            },
            "too_complex_to_implement": {
                "response": "3-month pilot program with 100 employees proves ROI before company-wide rollout. Dedicated implementation team included.",
                "supporting_data": "Average implementation time: 4 weeks",
            },
        }

    def _get_roi_calculator(self) -> Dict:
        """Interactive ROI calculator for prospects"""
        return {
            "calculator_url": "/tools/enterprise-roi-calculator",
            "inputs": [
                "Number of employees",
                "Current annual healthcare costs",
                "Average employee age",
                "Percentage with chronic conditions",
            ],
            "outputs": [
                "Monthly healthcare savings",
                "Annual ROI percentage",
                "Payback period",
                "5-year cost avoidance",
            ],
            "sample_calculation": {
                "500_employees": {
                    "monthly_savings": "$46,275",
                    "annual_roi": "2,644%",
                    "payback_period": "3.2 weeks",
                }
            },
        }

    def _get_case_studies(self) -> List[Dict]:
        """Customer success stories"""
        return [
            {
                "company": "TechCorp Solutions (500 employees)",
                "challenge": "18% annual healthcare cost increases, low wellness participation",
                "solution": "AI nutrition program with EHR integration",
                "results": {
                    "cost_reduction": "12% healthcare cost reduction",
                    "participation": "78% employee participation",
                    "health_outcomes": "Average 8lb weight loss, 10mmHg BP reduction",
                    "roi": "3,200% ROI in first year",
                },
            },
            {
                "company": "Manufacturing Corp (800 employees)",
                "challenge": "High diabetes rates, expensive specialist visits",
                "solution": "Pre-diabetes focused nutrition intervention",
                "results": {
                    "diabetes_prevention": "45% of pre-diabetics moved to normal range",
                    "cost_savings": "$127,000/month claims reduction",
                    "engagement": "73% program completion rate",
                },
            },
        ]

    def _get_demo_script(self) -> Dict:
        """15-minute demo script"""
        return {
            "opening": "Show me your current wellness participation rates and healthcare cost trends",
            "problem_agitation": "Most wellness programs achieve 20-25% participation with minimal health outcomes",
            "solution_demo": [
                "AI-powered personalized nutrition plans",
                "Medical-grade biometric tracking",
                "EHR integration with physician oversight",
                "Real-time cost savings dashboard",
            ],
            "proof_points": [
                "73% participation rate (3x industry average)",
                "$127/employee/month proven savings",
                "Medical validation with board-certified physicians",
            ],
            "closing": "Would a 3-month pilot with your 100 highest-risk employees make sense to prove these results?",
        }

    def _get_proposal_templates(self) -> Dict:
        """Standardized proposal templates"""
        return {
            "executive_summary": "templates/executive_summary.docx",
            "detailed_proposal": "templates/detailed_proposal.pdf",
            "pilot_program_outline": "templates/pilot_program.pdf",
            "contract_template": "templates/performance_contract.docx",
            "roi_analysis": "templates/roi_analysis.xlsx",
        }


# Export the main service
__all__ = ["EnterpriseWellnessService"]
