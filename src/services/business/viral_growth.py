"""
Viral Growth Engine - Family Savings Challenges

Real viral mechanics that actually work. Not fake "share for a discount" BS.
People share when they're WINNING and want to brag about it.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FamilyChallenge:
    """A family savings challenge"""

    challenge_id: str
    family_id: str
    month: str
    savings_goal: Decimal
    actual_savings: Decimal
    rank: int
    reward: Optional[str] = None


class ViralGrowthEngine:
    """
    Actual viral mechanics that work:

    1. Family Savings Leaderboard - People love competition + bragging rights
    2. Unlock premium by inviting - Clear incentive, not just "share for discount"
    3. Family challenges - Group dynamics drive sharing
    4. Social proof - Show real families saving real money

    Target viral coefficient: 1.3 (each user brings 1.3 new users)
    """

    def __init__(self):
        self.challenges: Dict[str, FamilyChallenge] = {}
        self.leaderboards: Dict[str, List] = {}
        self.referral_tracking: Dict[str, List] = {}

    def create_family_savings_challenge(self) -> Dict:
        """
        Monthly family savings challenge

        Families compete to save the most money on groceries
        Winner gets $50 grocery credit + bragging rights

        Why this works:
        - Competition drives engagement
        - Financial incentive is real
        - Winners naturally share/brag (free marketing)
        - Losers want to win next month (retention)
        """
        month = datetime.now().strftime("%Y-%m")

        return {
            "challenge_id": f"savings_challenge_{month}",
            "month": month,
            "title": "💰 Family Savings Challenge",
            "description": (
                "Which family can save the most on groceries this month? "
                "Top 3 families win prizes!"
            ),
            "prizes": {
                "1st_place": "$50 grocery credit + Champion badge",
                "2nd_place": "$25 grocery credit",
                "3rd_place": "$10 grocery credit",
                "top_10": "Premium subscription for 1 month",
            },
            "mechanics": {
                "entry": "Free for all families using Family tier",
                "tracking": "Automatic - we track your grocery savings",
                "duration": "1 month (resets monthly)",
                "minimum_families": 3,  # Need at least 3 to be competitive
            },
            "sharing_incentives": {
                "invite_family": "Invite other families to increase prize pool",
                "social_brag": "Share your rank to Facebook/Instagram",
                "prize_multiplier": "+$10 to prize pool for every 10 families",
            },
            "viral_coefficient_target": 1.3,
        }

    def get_family_leaderboard(self, month: Optional[str] = None) -> Dict:
        """
        Get current month's leaderboard

        Show real families, real savings, real competition
        This is what people share when they're winning
        """
        if not month:
            month = datetime.now().strftime("%Y-%m")

        # In production, query from database
        # For now, generate example leaderboard
        leaderboard = self._generate_example_leaderboard(month)

        return {
            "month": month,
            "total_families": len(leaderboard),
            "total_savings": sum(f["savings"] for f in leaderboard),
            "avg_savings_per_family": sum(f["savings"] for f in leaderboard) / len(leaderboard),
            "leaderboard": leaderboard[:10],  # Top 10
            "your_rank": None,  # Filled in for specific user
            "share_message": self._generate_share_message(leaderboard),
        }

    def _generate_example_leaderboard(self, month: str) -> List[Dict]:
        """Generate example leaderboard for demonstration"""
        families = [
            {"name": "The Johnsons", "members": 4, "savings": 287.45, "rank": 1},
            {"name": "The Smiths", "members": 5, "savings": 265.30, "rank": 2},
            {"name": "The Garcia Family", "members": 6, "savings": 243.20, "rank": 3},
            {"name": "The Patels", "members": 3, "savings": 198.75, "rank": 4},
            {"name": "The Nguyens", "members": 4, "savings": 187.50, "rank": 5},
            {"name": "The Browns", "members": 5, "savings": 176.25, "rank": 6},
            {"name": "The Lees", "members": 3, "savings": 165.80, "rank": 7},
            {"name": "The Martinezes", "members": 6, "savings": 154.90, "rank": 8},
            {"name": "The Wilsons", "members": 4, "savings": 143.60, "rank": 9},
            {"name": "The Andersons", "members": 4, "savings": 132.45, "rank": 10},
        ]

        return families

    def _generate_share_message(self, leaderboard: List[Dict]) -> str:
        """Generate shareable message for social media"""
        if not leaderboard:
            return ""

        winner = leaderboard[0]
        return (
            f"🏆 {winner['name']} saved ${winner['savings']:.2f} on groceries this month! "
            f"Join our family savings challenge and compete to save more. "
            f"#GrocerySavingsChallenge #FamilyFinance"
        )

    def create_referral_program(self) -> Dict:
        """
        Referral program that actually works

        Not "get 10% off" - that's lame
        Instead: "Unlock premium features by helping friends save money"
        """
        return {
            "mechanics": {
                "invite_3_families": {
                    "reward": "Unlock Premium features for 1 month",
                    "why_it_works": "Clear value, helps friends, meaningful reward",
                },
                "invite_10_families": {
                    "reward": "Upgrade to Family tier FREE for 3 months",
                    "why_it_works": "Exclusive club feeling, significant value",
                },
                "referred_family_subscribes": {
                    "reward": "$5 credit per paying family",
                    "why_it_works": "Aligned incentives - we all win",
                },
            },
            "sharing_tools": {
                "custom_referral_link": "share.nutritionist.app/yourname",
                "pre_written_messages": [
                    "We've saved $265 on groceries this month with this app! Try it: [link]",
                    "Stop overspending on food. This AI planner saved us $$$: [link]",
                    "Family meal planning that actually saves money: [link]",
                ],
                "social_proof": "Show how much YOU saved when sharing",
            },
            "viral_coefficient_drivers": {
                "target": 1.3,
                "current_tactics": [
                    "Family challenges (competitive sharing)",
                    "Unlock features via referrals (clear incentive)",
                    "Social proof (show real savings)",
                    "Pre-written messages (reduce friction)",
                ],
            },
        }

    def track_viral_coefficient(self, time_period_days: int = 30) -> Dict:
        """
        Track actual viral coefficient

        Formula: (New users from referrals) / (Active users who referred)
        Target: > 1.2 for sustainable growth
        """
        # In production, query real data
        # For now, return target metrics

        return {
            "time_period_days": time_period_days,
            "metrics": {
                "active_users": 1000,
                "users_who_referred": 350,  # 35% referral rate
                "new_users_from_referrals": 455,  # 1.3 per referrer
                "viral_coefficient": 1.3,
                "interpretation": "Sustainable viral growth - each user brings 1.3 new users",
            },
            "goal": {
                "viral_coefficient": 1.3,
                "status": "On track",
                "impact": "100 users → 130 → 169 → 220 → 286 (in 4 months)",
            },
            "optimization_opportunities": [
                "Increase referral rate from 35% to 45% (+115 new users/month)",
                "Improve referral conversion from 1.3 to 1.5 (+70 new users/month)",
                "Add B2B2C partnerships (10x growth potential)",
            ],
        }

    def design_b2b2c_viral_loop(self) -> Dict:
        """
        B2B2C distribution = The real growth hack

        Partner with:
        - Employers (wellness benefit)
        - Insurance companies (healthy eating incentive)
        - Grocery stores (customer acquisition)

        They distribute to THEIR customers/employees
        """
        return {
            "employer_partnership": {
                "pitch": "Employee wellness benefit that pays for itself",
                "pricing": "$2/employee/month",
                "employee_cost": "$0 (employer pays)",
                "value_prop": [
                    "Employees save $65/month on groceries",
                    "Healthier eating = lower healthcare costs",
                    "Easy benefit to promote (saves employees money)",
                ],
                "viral_mechanism": "Employees share with family/friends",
                "scale_potential": "1 employer = 100-5,000 users instantly",
            },
            "insurance_partnership": {
                "pitch": "Reduce claims through better nutrition",
                "pricing": "$1.50/member/month",
                "member_cost": "$0 (insurance pays)",
                "value_prop": [
                    "Preventive health through nutrition",
                    "Measurable impact on chronic disease",
                    "Member retention tool (valuable benefit)",
                ],
                "viral_mechanism": "Members share success stories",
                "scale_potential": "1 insurance company = 10,000-1M members",
            },
            "grocery_partnership": {
                "pitch": "Customer acquisition + increased basket size",
                "pricing": "Commission-based (no upfront cost)",
                "customer_cost": "$0 initially, then $9.99-19.99/mo",
                "value_prop": [
                    "Drive customers to specific stores",
                    "Increase basket size 15-20%",
                    "Data insights on shopping patterns",
                ],
                "viral_mechanism": "In-store promotion + loyalty program",
                "scale_potential": "1 regional chain = 50,000-500,000 customers",
            },
            "why_b2b2c_wins": [
                "Zero customer acquisition cost (partner pays)",
                "Instant distribution (partner's customer base)",
                "Higher conversion (endorsed by trusted brand)",
                "Sustainable (recurring B2B revenue)",
                "Scalable (each partner = thousands of users)",
            ],
            "recommended_approach": {
                "month_1": "Build consumer app proof of concept",
                "month_2": "Get 1-2 regional grocery partnerships",
                "month_3": "Pitch to small/medium employers (50-500 employees)",
                "month_4": "Close first employer partnership",
                "month_5": "Use employer success story for insurance pitch",
                "month_6": "Scale B2B2C as primary growth channel",
            },
        }

    def calculate_growth_projections(self, starting_users: int = 100) -> Dict:
        """
        Growth projections with different strategies

        Show the difference between:
        1. Consumer-only (traditional growth)
        2. Consumer + viral (1.3 coefficient)
        3. Consumer + viral + B2B2C (the real play)
        """
        months = 12

        # Scenario 1: Consumer-only (paid ads, SEO)
        consumer_only = [starting_users]
        monthly_growth_rate = 1.15  # 15% MoM
        for _ in range(months - 1):
            consumer_only.append(int(consumer_only[-1] * monthly_growth_rate))

        # Scenario 2: Consumer + Viral (1.3 coefficient)
        consumer_viral = [starting_users]
        viral_coefficient = 1.3
        for _ in range(months - 1):
            new_users = int(
                consumer_viral[-1] * 0.35 * viral_coefficient
            )  # 35% refer, 1.3 coefficient
            growth_users = int(consumer_viral[-1] * 0.10)  # Base 10% growth
            consumer_viral.append(consumer_viral[-1] + new_users + growth_users)

        # Scenario 3: Consumer + Viral + B2B2C
        consumer_viral_b2b = [starting_users]
        b2b_partnerships = [
            (2, 500),  # Month 2: First grocery partnership
            (4, 2000),  # Month 4: First employer partnership
            (6, 5000),  # Month 6: Larger employer partnership
            (8, 1000),  # Month 8: Second grocery partnership
            (10, 10000),  # Month 10: Insurance partnership
        ]

        for month in range(1, months):
            # Base viral growth
            new_users = int(consumer_viral_b2b[-1] * 0.35 * viral_coefficient)
            growth_users = int(consumer_viral_b2b[-1] * 0.10)

            # B2B2C partnerships
            b2b_users = sum(users for m, users in b2b_partnerships if m == month)

            consumer_viral_b2b.append(consumer_viral_b2b[-1] + new_users + growth_users + b2b_users)

        return {
            "starting_users": starting_users,
            "months": months,
            "scenarios": {
                "consumer_only": {
                    "month_1": consumer_only[0],
                    "month_6": consumer_only[5],
                    "month_12": consumer_only[11],
                    "growth_rate": "15% MoM",
                    "final_users": consumer_only[-1],
                },
                "consumer_viral": {
                    "month_1": consumer_viral[0],
                    "month_6": consumer_viral[5],
                    "month_12": consumer_viral[11],
                    "viral_coefficient": viral_coefficient,
                    "final_users": consumer_viral[-1],
                },
                "consumer_viral_b2b2c": {
                    "month_1": consumer_viral_b2b[0],
                    "month_6": consumer_viral_b2b[5],
                    "month_12": consumer_viral_b2b[11],
                    "partnerships": len(b2b_partnerships),
                    "final_users": consumer_viral_b2b[-1],
                },
            },
            "comparison": {
                "consumer_only_final": consumer_only[-1],
                "consumer_viral_final": consumer_viral[-1],
                "consumer_viral_b2b2c_final": consumer_viral_b2b[-1],
                "b2b2c_multiplier": f"{consumer_viral_b2b[-1] / consumer_only[-1]:.1f}x",
            },
            "recommendation": "Focus on B2B2C after proving consumer product-market fit",
        }
