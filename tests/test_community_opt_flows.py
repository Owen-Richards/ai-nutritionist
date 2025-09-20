"""Integration tests for community opt-in/opt-out flows."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from services.community.service import CommunityService, JoinCrewCommand, LeaveCrewCommand
from services.community.repository import CommunityRepository
from services.community.models import Crew, CrewMember, CrewType, MembershipStatus
from services.community.anonymization import AnonymizationService


@pytest.fixture
def community_repository():
    """Mock community repository."""
    return Mock(spec=CommunityRepository)


@pytest.fixture
def anonymization_service():
    """Mock anonymization service."""
    return Mock(spec=AnonymizationService)


@pytest.fixture
def community_service(community_repository, anonymization_service):
    """Community service with mocked dependencies."""
    return CommunityService(community_repository, anonymization_service)


@pytest.fixture
def sample_crew():
    """Sample crew for testing."""
    return Crew(
        crew_id="crew_123",
        name="Wellness Warriors",
        crew_type=CrewType.WEIGHT_LOSS,
        description="Support group for weight loss journey",
        max_members=25,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )


class TestOptInOptOutFlows:
    """Test user opt-in and opt-out workflows."""
    
    def test_successful_opt_in_flow(self, community_service, community_repository, sample_crew):
        """Test complete opt-in flow with notifications."""
        # Setup mocks
        community_repository.get_crew.return_value = sample_crew
        community_repository.get_user_membership.return_value = None
        community_repository.get_crew_member_count.return_value = 10
        community_repository.save_member.return_value = True
        
        # Test join command with full consent
        command = JoinCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            privacy_consent=True,
            notifications_enabled=True
        )
        
        result = community_service.join_crew(command, "John Doe")
        
        # Verify success
        assert result.success is True
        assert result.member is not None
        assert result.member.privacy_consent is True
        assert result.member.notifications_enabled is True
        assert result.welcome_message is not None
        
        # Verify repository calls
        community_repository.save_member.assert_called_once()
        saved_member = community_repository.save_member.call_args[0][0]
        assert saved_member.user_id == "user_123"
        assert saved_member.crew_id == "crew_123"
        assert saved_member.status == MembershipStatus.ACTIVE
    
    def test_opt_in_without_notifications(self, community_service, community_repository, sample_crew):
        """Test opt-in with notifications disabled."""
        # Setup mocks
        community_repository.get_crew.return_value = sample_crew
        community_repository.get_user_membership.return_value = None
        community_repository.get_crew_member_count.return_value = 10
        community_repository.save_member.return_value = True
        
        # Test join command without notifications
        command = JoinCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            privacy_consent=True,
            notifications_enabled=False
        )
        
        result = community_service.join_crew(command, "John Doe")
        
        # Verify success but no welcome SMS
        assert result.success is True
        assert result.member.notifications_enabled is False
        assert result.welcome_message is None  # No SMS sent
    
    def test_opt_in_without_privacy_consent(self, community_service, community_repository, sample_crew):
        """Test opt-in failure without privacy consent."""
        # Setup mocks
        community_repository.get_crew.return_value = sample_crew
        
        # Test join command without privacy consent
        command = JoinCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            privacy_consent=False,
            notifications_enabled=True
        )
        
        result = community_service.join_crew(command, "John Doe")
        
        # Verify failure
        assert result.success is False
        assert "privacy consent" in result.error_message.lower()
        assert result.member is None
    
    def test_opt_in_crew_full(self, community_service, community_repository, sample_crew):
        """Test opt-in failure when crew is full."""
        # Setup mocks
        community_repository.get_crew.return_value = sample_crew
        community_repository.get_user_membership.return_value = None
        community_repository.get_crew_member_count.return_value = sample_crew.max_members
        
        # Test join command
        command = JoinCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            privacy_consent=True,
            notifications_enabled=True
        )
        
        result = community_service.join_crew(command, "John Doe")
        
        # Verify failure
        assert result.success is False
        assert "full" in result.error_message.lower()
        assert result.member is None
    
    def test_opt_in_already_member(self, community_service, community_repository, sample_crew):
        """Test opt-in when user is already a member."""
        existing_member = CrewMember(
            member_id="member_456",
            crew_id="crew_123",
            user_id="user_123",
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
            privacy_consent=True,
            notifications_enabled=True
        )
        
        # Setup mocks
        community_repository.get_crew.return_value = sample_crew
        community_repository.get_user_membership.return_value = existing_member
        
        # Test join command
        command = JoinCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            privacy_consent=True,
            notifications_enabled=True
        )
        
        result = community_service.join_crew(command, "John Doe")
        
        # Verify failure
        assert result.success is False
        assert "already" in result.error_message.lower()
        assert result.member is None
    
    def test_successful_opt_out_flow(self, community_service, community_repository):
        """Test complete opt-out flow."""
        existing_member = CrewMember(
            member_id="member_456",
            crew_id="crew_123",
            user_id="user_123",
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
            privacy_consent=True,
            notifications_enabled=True
        )
        
        # Setup mocks
        community_repository.get_user_membership.return_value = existing_member
        community_repository.update_member_status.return_value = True
        
        # Test leave command
        command = LeaveCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            reason="No longer interested"
        )
        
        success = community_service.leave_crew(command)
        
        # Verify success
        assert success is True
        
        # Verify repository calls
        community_repository.update_member_status.assert_called_once_with(
            "member_456", MembershipStatus.LEFT
        )
    
    def test_opt_out_not_member(self, community_service, community_repository):
        """Test opt-out when user is not a member."""
        # Setup mocks
        community_repository.get_user_membership.return_value = None
        
        # Test leave command
        command = LeaveCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            reason="No longer interested"
        )
        
        success = community_service.leave_crew(command)
        
        # Verify failure
        assert success is False
    
    def test_notification_preferences_update(self, community_service, community_repository):
        """Test updating notification preferences."""
        existing_member = CrewMember(
            member_id="member_456",
            crew_id="crew_123",
            user_id="user_123",
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
            privacy_consent=True,
            notifications_enabled=True
        )
        
        # Setup mocks
        community_repository.get_user_membership.return_value = existing_member
        community_repository.update_member_preferences.return_value = True
        
        # Test notification preference update
        success = community_service.update_notification_preferences(
            user_id="user_123",
            crew_id="crew_123",
            notifications_enabled=False
        )
        
        # Verify success
        assert success is True
        
        # Verify repository call
        community_repository.update_member_preferences.assert_called_once_with(
            "member_456", notifications_enabled=False
        )
    
    def test_privacy_consent_withdrawal(self, community_service, community_repository, anonymization_service):
        """Test privacy consent withdrawal and data anonymization."""
        existing_member = CrewMember(
            member_id="member_456",
            crew_id="crew_123",
            user_id="user_123",
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
            privacy_consent=True,
            notifications_enabled=True
        )
        
        # Setup mocks
        community_repository.get_user_membership.return_value = existing_member
        community_repository.update_member_preferences.return_value = True
        anonymization_service.anonymize_user_data.return_value = True
        
        # Test privacy consent withdrawal
        success = community_service.withdraw_privacy_consent(
            user_id="user_123",
            crew_id="crew_123"
        )
        
        # Verify success
        assert success is True
        
        # Verify privacy consent was updated
        community_repository.update_member_preferences.assert_called_once_with(
            "member_456", privacy_consent=False
        )
        
        # Verify user data was anonymized
        anonymization_service.anonymize_user_data.assert_called_once_with("user_123")
    
    def test_gdpr_data_deletion(self, community_service, community_repository, anonymization_service):
        """Test GDPR-compliant data deletion."""
        existing_member = CrewMember(
            member_id="member_456",
            crew_id="crew_123",
            user_id="user_123",
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
            privacy_consent=True,
            notifications_enabled=True
        )
        
        # Setup mocks
        community_repository.get_user_membership.return_value = existing_member
        community_repository.delete_user_data.return_value = True
        anonymization_service.delete_user_data.return_value = True
        
        # Test data deletion request
        success = community_service.delete_user_data("user_123")
        
        # Verify success
        assert success is True
        
        # Verify data deletion in repository
        community_repository.delete_user_data.assert_called_once_with("user_123")
        
        # Verify data deletion in anonymization service
        anonymization_service.delete_user_data.assert_called_once_with("user_123")


class TestConsentValidation:
    """Test consent validation and compliance."""
    
    def test_explicit_consent_required(self, community_service, community_repository, sample_crew):
        """Test that explicit consent is required for all data processing."""
        # Setup mocks
        community_repository.get_crew.return_value = sample_crew
        
        # Test without explicit consent
        command = JoinCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            privacy_consent=None,  # No explicit consent
            notifications_enabled=True
        )
        
        result = community_service.join_crew(command, "John Doe")
        
        # Verify failure
        assert result.success is False
        assert "consent" in result.error_message.lower()
    
    def test_consent_recording(self, community_service, community_repository, sample_crew):
        """Test that consent decisions are properly recorded."""
        # Setup mocks
        community_repository.get_crew.return_value = sample_crew
        community_repository.get_user_membership.return_value = None
        community_repository.get_crew_member_count.return_value = 10
        community_repository.save_member.return_value = True
        
        # Test with explicit consent
        command = JoinCrewCommand(
            user_id="user_123",
            crew_id="crew_123",
            privacy_consent=True,
            notifications_enabled=True
        )
        
        result = community_service.join_crew(command, "John Doe")
        
        # Verify consent was recorded
        assert result.success is True
        saved_member = community_repository.save_member.call_args[0][0]
        assert saved_member.privacy_consent is True
        assert saved_member.consent_timestamp is not None
    
    def test_consent_audit_trail(self, community_service, community_repository):
        """Test that consent changes create an audit trail."""
        existing_member = CrewMember(
            member_id="member_456",
            crew_id="crew_123",
            user_id="user_123",
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
            privacy_consent=True,
            notifications_enabled=True
        )
        
        # Setup mocks
        community_repository.get_user_membership.return_value = existing_member
        community_repository.update_member_preferences.return_value = True
        community_repository.log_consent_change.return_value = True
        
        # Test consent withdrawal
        success = community_service.withdraw_privacy_consent(
            user_id="user_123",
            crew_id="crew_123"
        )
        
        # Verify audit trail was created
        assert success is True
        community_repository.log_consent_change.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
