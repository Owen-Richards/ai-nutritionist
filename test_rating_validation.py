#!/usr/bin/env python3
"""Quick test to verify rating validation works."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pydantic import ValidationError
from src.api.schemas.plan import PlanFeedbackRequest

def test_rating_validation():
    """Test that rating validation works as expected."""
    
    # Test valid rating
    try:
        valid_feedback = PlanFeedbackRequest(
            user_id="test-user",
            plan_id="test-plan-123", 
            meal_id="meal-1",
            rating=5
        )
        print("✅ Valid rating (5) accepted")
    except ValidationError as e:
        print(f"❌ Valid rating rejected: {e}")
        return False
    
    # Test invalid rating (too high)
    try:
        invalid_feedback = PlanFeedbackRequest(
            user_id="test-user",
            plan_id="test-plan-123",
            meal_id="meal-1", 
            rating=7
        )
        print("❌ Invalid rating (7) was accepted - this should fail!")
        return False
    except ValidationError as e:
        print("✅ Invalid rating (7) correctly rejected")
        print(f"   Error details: {e}")
    
    # Test invalid rating (too low)
    try:
        invalid_feedback = PlanFeedbackRequest(
            user_id="test-user",
            plan_id="test-plan-123",
            meal_id="meal-1",
            rating=0
        )
        print("❌ Invalid rating (0) was accepted - this should fail!")
        return False
    except ValidationError as e:
        print("✅ Invalid rating (0) correctly rejected")
        print(f"   Error details: {e}")
    
    return True

if __name__ == "__main__":
    print("Testing rating validation...")
    success = test_rating_validation()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
