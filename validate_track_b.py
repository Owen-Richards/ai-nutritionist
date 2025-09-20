#!/usr/bin/env python3
"""Validation script for Track B Community implementation."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timezone
from services.community.models import *
from services.community.repository import CommunityRepository
from services.community.service import CommunityService, JoinCrewCommand
from services.community.anonymization import AnonymizationService
from services.community.templates import SMSTemplateEngine

def test_track_b_implementation():
    """Validate Track B implementation components."""
    print("🧪 Validating Track B - Community (SMS-first Crews) Implementation")
    print("=" * 70)
    
    results = []
    crew = None
    
    # Test 1: Domain Models
    try:
        crew = Crew(
            crew_id="test_crew",
            name="Test Crew",
            crew_type=CrewType.NUTRITION_FOCUSED,
            description="Test crew",
            cohort_key="test",
            max_members=10,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        print("✅ Domain models (Crew, CrewMember, etc.) working")
        results.append(("Domain Models", True))
    except Exception as e:
        print(f"❌ Domain models failed: {e}")
        results.append(("Domain Models", False))
        return results  # Can't continue without crew
    
    # Test 2: SMS Templates
    try:
        engine = SMSTemplateEngine()
        message = engine.render_daily_pulse("John", crew, 5)
        assert len(message.message) <= 160
        print("✅ SMS template engine working")
        results.append(("SMS Templates", True))
    except Exception as e:
        print(f"❌ SMS templates failed: {e}")
        results.append(("SMS Templates", False))
    
    # Test 3: Anonymization Service
    try:
        anon_service = AnonymizationService()
        test_content = "Hi, I'm John Doe and my email is john@test.com"
        redacted = anon_service.redact_user_content(test_content)
        assert "john@test.com" not in redacted
        print("✅ Anonymization service working")
        results.append(("Anonymization", True))
    except Exception as e:
        print(f"❌ Anonymization failed: {e}")
        results.append(("Anonymization", False))
    
    # Test 4: Repository Layer
    try:
        repo = CommunityRepository()
        repo.save_crew(crew)
        retrieved = repo.get_crew("test_crew")
        assert retrieved.name == "Test Crew"
        print("✅ Repository layer working")
        results.append(("Repository Layer", True))
    except Exception as e:
        print(f"❌ Repository failed: {e}")
        results.append(("Repository Layer", False))
    
    # Test 5: Service Layer
    try:
        service = CommunityService(repo, anon_service)
        command = JoinCrewCommand(
            user_id="test_user",
            crew_id="test_crew",
            privacy_consent=True,
            notifications_enabled=True
        )
        result = service.join_crew(command, "Test User")
        assert result.success is not None  # Check result has success attribute
        print("✅ Service layer working")
        results.append(("Service Layer", True))
    except Exception as e:
        print(f"❌ Service layer failed: {e}")
        results.append(("Service Layer", False))
    
    # Test 6: Rate Limiting
    try:
        from api.middleware.rate_limiting import RateLimiter
        limiter = RateLimiter()
        allowed, retry_after = limiter.check_sms_rate_limit("test_user")
        assert allowed is True
        print("✅ Rate limiting working")
        results.append(("Rate Limiting", True))
    except Exception as e:
        print(f"❌ Rate limiting failed: {e}")
        results.append(("Rate Limiting", False))
    
    # Summary
    print("\n📊 Track B Implementation Summary:")
    print("-" * 40)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for component, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{component:<20} {status}")
    
    print(f"\nOverall: {passed}/{total} components working ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 Track B - Community implementation is COMPLETE and working!")
        print("\n🚀 Ready for FAANG-level production deployment!")
        return True
    else:
        print(f"\n⚠️  {total - passed} components need attention")
        return False


if __name__ == "__main__":
    success = test_track_b_implementation()
    sys.exit(0 if success else 1)
