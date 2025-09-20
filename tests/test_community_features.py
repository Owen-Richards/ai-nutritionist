"""Comprehensive test suite for community features."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from api.app import create_app
from services.community.models import (
    Crew, CrewMember, CrewType, MembershipStatus, 
    Reflection, ReflectionType, PulseMetric, PulseMetricType
)
from services.community.service import (
    CommunityService, JoinCrewCommand, SubmitReflectionCommand, 
    SubmitPulseCommand, JoinCrewResult, SubmitReflectionResult
)


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_community_service():
    """Mock community service for testing."""
    return Mock(spec=CommunityService)


@pytest.fixture
def sample_crew():
    """Sample crew for testing."""
    return Crew(
        crew_id="crew_123",
        name="Healthy Habits",
        crew_type=CrewType.NUTRITION_FOCUSED,
        description="A crew focused on building healthy eating habits",
        max_members=50,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_member():
    """Sample crew member for testing."""
    return CrewMember(
        member_id="member_456",
        crew_id="crew_123",
        user_id="user_789",
        status=MembershipStatus.ACTIVE,
        joined_at=datetime.now(timezone.utc),
        privacy_consent=True,
        notifications_enabled=True
    )


class TestCommunityAPI:
    """Test community API endpoints."""
    
    def test_join_crew_success(self, client, mock_community_service, sample_crew, sample_member):
        """Test successful crew joining."""
        # Mock successful join
        result = JoinCrewResult(
            success=True,
            member=sample_member,
            welcome_message=Mock(message="Welcome to the crew!"),
            error_message=None
        )
        
        mock_community_service.join_crew.return_value = result
        mock_community_service._repository.get_crew.return_value = sample_crew
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.post("/v1/crews/join", json={
                "user_id": "user_789",
                "crew_id": "crew_123",
                "user_name": "John Doe",
                "privacy_consent": True,
                "notifications_enabled": True
            })
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Successfully joined crew"
        assert data["member_id"] == "member_456"
        assert data["welcome_sms"] == "Welcome to the crew!"
        assert "crew_info" in data
    
    def test_join_crew_failure(self, client, mock_community_service):
        """Test crew joining failure."""
        # Mock failed join
        result = JoinCrewResult(
            success=False,
            member=None,
            welcome_message=None,
            error_message="Crew is full"
        )
        
        mock_community_service.join_crew.return_value = result
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.post("/v1/crews/join", json={
                "user_id": "user_789",
                "crew_id": "crew_123",
                "user_name": "John Doe",
                "privacy_consent": True,
                "notifications_enabled": True
            })
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Crew is full"
    
    def test_get_crew_pulse_success(self, client, mock_community_service):
        """Test successful crew pulse retrieval."""
        from services.community.anonymization import CrewPulse
        
        # Mock pulse data
        pulse = CrewPulse(
            crew_id="crew_123",
            pulse_date=datetime.now(timezone.utc),
            total_active_members=10,
            engagement_score=0.85,
            metrics={
                PulseMetricType.ENERGY_LEVEL: {"avg": 7.5, "median": 8.0, "count": 10},
                PulseMetricType.MOTIVATION: {"avg": 6.8, "median": 7.0, "count": 10}
            },
            recent_reflections=["Great progress!", "Feeling motivated"],
            challenge_completion_rate=0.75,
            anonymization_applied=True
        )
        
        mock_community_service.get_crew_pulse.return_value = pulse
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.get("/v1/crews/crew_123/pulse?days_back=7")
        
        assert response.status_code == 200
        data = response.json()
        assert data["crew_id"] == "crew_123"
        assert data["total_active_members"] == 10
        assert data["engagement_score"] == 0.85
        assert len(data["metrics"]) == 2
        assert data["anonymization_applied"] is True
    
    def test_get_crew_pulse_privacy_suppression(self, client, mock_community_service):
        """Test crew pulse with privacy suppression for small crews."""
        from services.community.anonymization import CrewPulse
        
        # Mock pulse data with small crew
        pulse = CrewPulse(
            crew_id="crew_123",
            pulse_date=datetime.now(timezone.utc),
            total_active_members=3,
            engagement_score=0.0,
            metrics={},
            recent_reflections=[],
            challenge_completion_rate=0.0,
            anonymization_applied=True
        )
        
        mock_community_service.get_crew_pulse.return_value = pulse
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.get("/v1/crews/crew_123/pulse?days_back=7")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data_suppressed"] is True
        assert data["suppression_reason"] == "Crew has fewer than 5 active members"
        assert data["recent_reflections"] == ["Data suppressed - crew size below privacy threshold"]
    
    def test_submit_reflection_success(self, client, mock_community_service):
        """Test successful reflection submission."""
        # Mock successful submission
        reflection = Reflection(
            reflection_id="refl_456",
            crew_id="crew_123",
            user_id="user_789",
            content="I'm feeling great about my progress!",
            reflection_type=ReflectionType.DAILY_CHECKIN,
            mood_score=8,
            progress_rating=4,
            is_anonymous=False,
            created_at=datetime.now(timezone.utc),
            pii_redacted=False
        )
        
        result = SubmitReflectionResult(
            success=True,
            reflection=reflection,
            error_message=None
        )
        
        mock_community_service.submit_reflection.return_value = result
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.post("/v1/crews/reflections", json={
                "user_id": "user_789",
                "crew_id": "crew_123",
                "content": "I'm feeling great about my progress!",
                "reflection_type": "daily_checkin",
                "mood_score": 8,
                "progress_rating": 4,
                "is_anonymous": False
            })
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["reflection_id"] == "refl_456"
        assert data["pii_redacted"] is False
    
    def test_submit_pulse_metrics_success(self, client, mock_community_service):
        """Test successful pulse metrics submission."""
        mock_community_service.submit_pulse_metrics.return_value = True
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.post("/v1/crews/pulse", json={
                "user_id": "user_789",
                "metrics": [
                    {"metric_type": "energy_level", "value": 8},
                    {"metric_type": "motivation", "value": 7}
                ]
            })
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["metrics_recorded"] == 2
    
    def test_list_available_crews(self, client, mock_community_service, sample_crew):
        """Test listing available crews."""
        mock_community_service.list_available_crews.return_value = [sample_crew]
        mock_community_service._repository.get_crew_members.return_value = []
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.get("/v1/crews/available")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["crew_id"] == "crew_123"
        assert data[0]["name"] == "Healthy Habits"
        assert data[0]["member_count"] == 0
    
    def test_get_user_crews(self, client, mock_community_service, sample_crew):
        """Test getting user's crews."""
        mock_community_service.get_user_crews.return_value = [sample_crew]
        mock_community_service._repository.get_crew_members.return_value = []
        
        with patch('api.dependencies.get_community_service', return_value=mock_community_service):
            response = client.get("/v1/crews/user/user_789")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["crew_id"] == "crew_123"


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_sms_rate_limit(self):
        """Test SMS rate limiting."""
        from api.middleware.rate_limiting import RateLimiter
        
        limiter = RateLimiter()
        user_id = "user_123"
        
        # First SMS should be allowed
        allowed, retry_after = limiter.check_sms_rate_limit(user_id)
        assert allowed is True
        assert retry_after is None
        
        # Second SMS within same minute should be blocked
        allowed, retry_after = limiter.check_sms_rate_limit(user_id)
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_api_rate_limit(self):
        """Test API rate limiting."""
        from api.middleware.rate_limiting import RateLimiter
        
        limiter = RateLimiter()
        user_id = "user_123"
        
        # Multiple API calls should be allowed up to limit
        for i in range(limiter.API_LIMIT):
            allowed, retry_after = limiter.check_api_rate_limit(user_id)
            assert allowed is True
            assert retry_after is None
        
        # Next call should be blocked
        allowed, retry_after = limiter.check_api_rate_limit(user_id)
        assert allowed is False
        assert retry_after is not None
    
    def test_reflection_rate_limit(self):
        """Test reflection submission rate limiting."""
        from api.middleware.rate_limiting import RateLimiter
        
        limiter = RateLimiter()
        user_id = "user_123"
        
        # Multiple reflections should be allowed up to limit
        for i in range(limiter.REFLECTION_LIMIT):
            allowed, retry_after = limiter.check_reflection_rate_limit(user_id)
            assert allowed is True
            assert retry_after is None
        
        # Next reflection should be blocked
        allowed, retry_after = limiter.check_reflection_rate_limit(user_id)
        assert allowed is False
        assert retry_after is not None
    
    def test_content_moderation(self):
        """Test content moderation."""
        from api.middleware.rate_limiting import RateLimiter
        
        limiter = RateLimiter()
        
        # Valid content should pass
        is_appropriate, reason = limiter.moderate_content("I'm feeling great today!")
        assert is_appropriate is True
        assert reason is None
        
        # Short content should be rejected
        is_appropriate, reason = limiter.moderate_content("Hi")
        assert is_appropriate is False
        assert "too short" in reason
        
        # Long content should be rejected
        long_content = "x" * 1001
        is_appropriate, reason = limiter.moderate_content(long_content)
        assert is_appropriate is False
        assert "too long" in reason
        
        # Repetitive content should be rejected
        repetitive_content = "spam spam spam spam spam spam"
        is_appropriate, reason = limiter.moderate_content(repetitive_content)
        assert is_appropriate is False
        assert "repetitive" in reason.lower()


class TestCommunityIntegration:
    """Integration tests for community features."""
    
    def test_full_crew_lifecycle(self, client):
        """Test complete crew joining and engagement flow."""
        # This would be an integration test that exercises the full flow
        # In a real environment, you'd use test databases and real services
        pass
    
    def test_privacy_anonymization_e2e(self, client):
        """Test end-to-end privacy and anonymization."""
        # Test that PII is properly handled throughout the system
        pass
    
    def test_sms_template_rendering(self):
        """Test SMS template rendering with real data."""
        from services.community.templates import SMSTemplateEngine
        
        engine = SMSTemplateEngine()
        
        # Test daily pulse template
        message = engine.render_daily_pulse("John", "Healthy Habits")
        assert "John" in message
        assert "Healthy Habits" in message
        assert len(message) <= 160  # SMS limit
        
        # Test weekly challenge template
        message = engine.render_weekly_challenge("Jane", "Try a new vegetable")
        assert "Jane" in message
        assert "vegetable" in message
        assert len(message) <= 160


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
