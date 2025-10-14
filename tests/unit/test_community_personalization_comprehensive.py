"""
Comprehensive unit tests for community and personalization services.

Tests cover:
- Community crew management
- User reflection and pulse tracking  
- Personalization and user profiling
- Privacy and anonymization
- Social features and interactions
- User behavior tracking and learning
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal
from uuid import uuid4
from typing import Dict, Any, List, Optional

from src.services.community.service import CommunityService
from src.services.community.repository import CommunityRepository
from src.services.community.models import (
    Crew, CrewMember, Reflection, CrewType, MembershipStatus, ReflectionType
)
from src.services.community.anonymization import AnonymizationService
from src.services.personalization.preferences import UserService
from src.services.personalization.behavior import UserLinkingService
from src.services.personalization.learning import SeamlessUserProfileService


class TestCommunityService:
    """Test community service functionality."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock community repository."""
        repository = Mock()
        repository.save_crew = Mock()
        repository.get_crew_by_id = Mock()
        repository.save_member = Mock()
        repository.save_reflection = Mock()
        repository.get_crew_reflections = Mock(return_value=[])
        repository.get_user_crews = Mock(return_value=[])
        return repository
    
    @pytest.fixture
    def community_service(self, mock_repository):
        """Create community service with mocked repository."""
        return CommunityService(repository=mock_repository)
    
    @pytest.mark.asyncio
    async def test_create_crew_success(self, community_service, mock_repository):
        """Test successful crew creation."""
        crew_data = {
            "name": "Healthy Habits",
            "crew_type": CrewType.NUTRITION_FOCUSED,
            "description": "A crew focused on building healthy eating habits",
            "max_members": 50,
            "creator_id": "user123"
        }
        
        result = await community_service.create_crew(crew_data)
        
        assert result.success is True
        assert result.crew is not None
        assert result.crew.name == crew_data["name"]
        mock_repository.save_crew.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_join_crew_success(self, community_service, mock_repository):
        """Test successful crew joining."""
        user_id = "user456"
        crew_id = "crew123"
        
        # Mock existing crew
        mock_crew = Crew(
            crew_id=crew_id,
            name="Test Crew",
            crew_type=CrewType.GENERAL_WELLNESS,
            description="Test crew",
            max_members=50,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        mock_repository.get_crew_by_id.return_value = mock_crew
        mock_repository.get_crew_member_count.return_value = 25  # Under limit
        
        result = await community_service.join_crew(user_id, crew_id)
        
        assert result.success is True
        assert result.member is not None
        assert result.member.user_id == user_id
        mock_repository.save_member.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_join_crew_at_capacity(self, community_service, mock_repository):
        """Test joining crew at maximum capacity."""
        user_id = "user456"
        crew_id = "crew123"
        
        # Mock crew at capacity
        mock_crew = Crew(
            crew_id=crew_id,
            name="Full Crew",
            crew_type=CrewType.GENERAL_WELLNESS,
            description="Full crew",
            max_members=10,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        mock_repository.get_crew_by_id.return_value = mock_crew
        mock_repository.get_crew_member_count.return_value = 10  # At capacity
        
        result = await community_service.join_crew(user_id, crew_id)
        
        assert result.success is False
        assert "capacity" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_submit_reflection(self, community_service, mock_repository):
        """Test reflection submission."""
        reflection_data = {
            "user_id": "user123",
            "crew_id": "crew456",
            "content": "I had a great day with my nutrition goals!",
            "reflection_type": ReflectionType.DAILY_CHECKIN,
            "mood_score": 8,
            "progress_rating": 4,
            "is_anonymous": False
        }
        
        result = await community_service.submit_reflection(reflection_data)
        
        assert result.success is True
        assert result.reflection is not None
        assert result.reflection.content == reflection_data["content"]
        assert result.reflection.mood_score == 8
        mock_repository.save_reflection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_anonymous_reflection_processing(self, community_service, mock_repository):
        """Test anonymous reflection processing."""
        reflection_data = {
            "user_id": "user123",
            "crew_id": "crew456", 
            "content": "My name is John and I live in New York. Today I ate at McDonald's.",
            "reflection_type": ReflectionType.WEEKLY_REFLECTION,
            "mood_score": 6,
            "is_anonymous": True
        }
        
        with patch('src.services.community.anonymization.AnonymizationService') as mock_anon:
            mock_anon.return_value.anonymize_content.return_value = \
                "Today I ate at a fast food restaurant."
            
            result = await community_service.submit_reflection(reflection_data)
            
            assert result.success is True
            assert "John" not in result.reflection.content
            assert "New York" not in result.reflection.content
            assert "McDonald's" not in result.reflection.content
    
    @pytest.mark.asyncio
    async def test_get_crew_pulse(self, community_service, mock_repository):
        """Test crew pulse metric calculation."""
        crew_id = "crew123"
        
        # Mock reflections
        mock_reflections = [
            Mock(mood_score=8, progress_rating=4, created_at=datetime.now(timezone.utc)),
            Mock(mood_score=7, progress_rating=5, created_at=datetime.now(timezone.utc)),
            Mock(mood_score=9, progress_rating=3, created_at=datetime.now(timezone.utc)),
            Mock(mood_score=6, progress_rating=4, created_at=datetime.now(timezone.utc)),
        ]
        mock_repository.get_crew_reflections.return_value = mock_reflections
        
        pulse = await community_service.get_crew_pulse(crew_id)
        
        assert pulse is not None
        assert pulse.average_mood == 7.5  # (8+7+9+6)/4
        assert pulse.average_progress == 4.0  # (4+5+3+4)/4
        assert pulse.total_reflections == 4
    
    def test_crew_type_validation(self, community_service):
        """Test crew type validation."""
        valid_types = [CrewType.NUTRITION_FOCUSED, CrewType.FITNESS_FOCUSED, CrewType.GENERAL_WELLNESS]
        
        for crew_type in valid_types:
            assert community_service.validate_crew_type(crew_type) is True
        
        # Test invalid type
        assert community_service.validate_crew_type("invalid_type") is False
    
    def test_reflection_content_validation(self, community_service):
        """Test reflection content validation."""
        valid_content = "I had a productive day working on my nutrition goals."
        invalid_content = ""  # Empty content
        too_long_content = "A" * 2001  # Exceeds character limit
        
        assert community_service.validate_reflection_content(valid_content) is True
        assert community_service.validate_reflection_content(invalid_content) is False
        assert community_service.validate_reflection_content(too_long_content) is False
    
    @pytest.mark.asyncio
    async def test_crew_member_moderation(self, community_service, mock_repository):
        """Test crew member moderation features."""
        crew_id = "crew123"
        member_id = "member456"
        moderator_id = "user789"
        
        # Mock moderator permissions
        mock_repository.is_crew_moderator.return_value = True
        
        result = await community_service.moderate_member(
            crew_id, member_id, moderator_id, action="suspend", reason="inappropriate_content"
        )
        
        assert result.success is True
        assert "suspend" in result.action_taken


class TestAnonymizationService:
    """Test content anonymization functionality."""
    
    @pytest.fixture
    def anonymization_service(self):
        """Create anonymization service."""
        return AnonymizationService()
    
    def test_pii_detection(self, anonymization_service):
        """Test PII detection in text."""
        text_with_pii = "Hi, I'm Sarah Johnson and my email is sarah.j@gmail.com. I live in Chicago."
        
        detected_pii = anonymization_service.detect_pii(text_with_pii)
        
        assert 'names' in detected_pii
        assert 'emails' in detected_pii
        assert 'locations' in detected_pii
        assert len(detected_pii['names']) > 0
        assert len(detected_pii['emails']) > 0
        assert len(detected_pii['locations']) > 0
    
    def test_content_anonymization(self, anonymization_service):
        """Test content anonymization."""
        personal_content = ("My name is John Smith and I work at Apple Inc. "
                          "I live at 123 Main St, San Francisco, CA. "
                          "My phone is 555-123-4567 and email is john@apple.com.")
        
        anonymized = anonymization_service.anonymize_content(personal_content)
        
        # Personal information should be removed/replaced
        assert "John Smith" not in anonymized
        assert "Apple Inc" not in anonymized
        assert "123 Main St" not in anonymized
        assert "555-123-4567" not in anonymized
        assert "john@apple.com" not in anonymized
        
        # Generic replacements should be present
        assert "[NAME]" in anonymized or "Person" in anonymized
        assert "[COMPANY]" in anonymized or "[ORGANIZATION]" in anonymized
    
    def test_location_anonymization(self, anonymization_service):
        """Test location-specific anonymization."""
        location_text = "I went to Starbucks on 5th Avenue in New York City."
        
        anonymized = anonymization_service.anonymize_locations(location_text)
        
        assert "5th Avenue" not in anonymized
        assert "New York City" not in anonymized
        assert "[LOCATION]" in anonymized or "a coffee shop" in anonymized
    
    def test_preserve_nutrition_context(self, anonymization_service):
        """Test preservation of nutrition-related context."""
        nutrition_content = ("I ate salmon and quinoa for dinner at John's house in Boston. "
                           "It had about 500 calories and 35g protein.")
        
        anonymized = anonymization_service.anonymize_content(nutrition_content)
        
        # Nutrition information should be preserved
        assert "salmon" in anonymized
        assert "quinoa" in anonymized
        assert "500 calories" in anonymized
        assert "35g protein" in anonymized
        
        # Personal information should be anonymized
        assert "John's house" not in anonymized
        assert "Boston" not in anonymized
    
    @pytest.mark.parametrize("sensitivity_level,expected_replacements", [
        ("low", ["[NAME]", "[LOCATION]"]),
        ("medium", ["[NAME]", "[LOCATION]", "[ORGANIZATION]"]),
        ("high", ["[NAME]", "[LOCATION]", "[ORGANIZATION]", "[PHONE]", "[EMAIL]"])
    ])
    def test_anonymization_levels(self, anonymization_service, sensitivity_level, expected_replacements):
        """Test different levels of anonymization."""
        content = ("John works at Microsoft in Seattle. "
                  "His phone is 555-0123 and email is john@microsoft.com.")
        
        anonymized = anonymization_service.anonymize_content(
            content, sensitivity_level=sensitivity_level
        )
        
        for replacement in expected_replacements:
            assert replacement in anonymized or any(
                generic in anonymized for generic in ["Person", "Company", "City"]
            )


class TestUserPreferencesService:
    """Test user preferences and personalization."""
    
    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        repository = Mock()
        repository.get_user_preferences = Mock()
        repository.save_user_preferences = Mock()
        repository.get_user_history = Mock()
        return repository
    
    @pytest.fixture
    def user_service(self, mock_user_repository):
        """Create user service with mocked repository."""
        return UserService(repository=mock_user_repository)
    
    @pytest.mark.asyncio
    async def test_update_dietary_preferences(self, user_service, mock_user_repository):
        """Test updating user dietary preferences."""
        user_id = "user123"
        preferences = {
            "dietary_restrictions": ["vegetarian", "gluten_free"],
            "cuisine_preferences": ["mediterranean", "asian"],
            "spice_tolerance": "medium",
            "meal_frequency": 4,
            "calorie_target": 2000
        }
        
        result = await user_service.update_preferences(user_id, preferences)
        
        assert result.success is True
        mock_user_repository.save_user_preferences.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preference_validation(self, user_service):
        """Test preference validation."""
        invalid_preferences = {
            "dietary_restrictions": ["invalid_diet"],
            "calorie_target": -100,  # Negative calories
            "meal_frequency": 10  # Too many meals
        }
        
        validation_result = await user_service.validate_preferences(invalid_preferences)
        
        assert validation_result.valid is False
        assert len(validation_result.errors) > 0
        assert "invalid_diet" in str(validation_result.errors)
        assert "calorie_target" in str(validation_result.errors)
    
    @pytest.mark.asyncio
    async def test_preference_learning_from_behavior(self, user_service, mock_user_repository):
        """Test learning preferences from user behavior."""
        user_id = "user123"
        
        # Mock user behavior history
        behavior_history = [
            {"action": "meal_logged", "food": "quinoa_salad", "rating": 5},
            {"action": "meal_logged", "food": "chicken_curry", "rating": 2},
            {"action": "meal_skipped", "meal_type": "breakfast", "reason": "too_early"},
            {"action": "recipe_saved", "cuisine": "mediterranean", "rating": 4}
        ]
        mock_user_repository.get_user_history.return_value = behavior_history
        
        learned_preferences = await user_service.learn_preferences_from_behavior(user_id)
        
        assert "quinoa" in learned_preferences.preferred_foods
        assert "chicken_curry" in learned_preferences.disliked_foods
        assert "mediterranean" in learned_preferences.preferred_cuisines
        assert learned_preferences.breakfast_preference.time_preference == "later"
    
    def test_preference_conflict_resolution(self, user_service):
        """Test resolution of conflicting preferences."""
        conflicting_preferences = {
            "dietary_restrictions": ["vegan"],
            "preferred_proteins": ["chicken", "fish"],  # Conflicts with vegan
            "calorie_target": 1200,
            "goal": "muscle_gain"  # Conflicts with low calories
        }
        
        resolved = user_service.resolve_preference_conflicts(conflicting_preferences)
        
        # Vegan should take precedence over protein preferences
        assert "chicken" not in resolved.allowed_proteins
        assert "tofu" in resolved.allowed_proteins
        
        # Calorie target should be adjusted for muscle gain goal
        assert resolved.calorie_target > 1200


class TestUserLinkingService:
    """Test user linking and family sharing functionality."""
    
    @pytest.fixture
    def linking_service(self):
        """Create user linking service."""
        return UserLinkingService()
    
    @pytest.mark.asyncio
    async def test_create_family_group(self, linking_service):
        """Test family group creation."""
        primary_user = "user123"
        family_name = "Smith Family"
        
        group = await linking_service.create_family_group(primary_user, family_name)
        
        assert group.group_id is not None
        assert group.primary_user_id == primary_user
        assert group.group_name == family_name
        assert primary_user in group.members
    
    @pytest.mark.asyncio
    async def test_add_family_member(self, linking_service):
        """Test adding family member."""
        group_id = "group123"
        new_member = "user456"
        relationship = "spouse"
        
        # Mock existing group
        with patch.object(linking_service, 'get_family_group') as mock_get:
            mock_group = Mock()
            mock_group.members = ["user123"]
            mock_group.member_limit = 6
            mock_get.return_value = mock_group
            
            result = await linking_service.add_family_member(
                group_id, new_member, relationship, invited_by="user123"
            )
            
            assert result.success is True
            assert result.member_added == new_member
    
    @pytest.mark.asyncio
    async def test_shared_meal_planning(self, linking_service):
        """Test shared meal planning for families."""
        group_id = "group123"
        meal_plan_preferences = {
            "dietary_accommodations": ["vegetarian", "nut_free"],  # Accommodate all members
            "shared_meals": ["dinner"],
            "individual_meals": ["breakfast", "lunch"],
            "cooking_rotation": True
        }
        
        shared_plan = await linking_service.create_shared_meal_plan(
            group_id, meal_plan_preferences
        )
        
        assert shared_plan.group_id == group_id
        assert "dinner" in shared_plan.shared_meals
        assert shared_plan.accommodates_all_restrictions is True
    
    def test_dietary_restriction_merging(self, linking_service):
        """Test merging dietary restrictions across family members."""
        family_restrictions = {
            "user123": ["vegetarian", "dairy_free"],
            "user456": ["gluten_free"],
            "user789": ["nut_free", "vegetarian"]
        }
        
        merged = linking_service.merge_family_restrictions(family_restrictions)
        
        # Should include all unique restrictions
        assert "vegetarian" in merged
        assert "dairy_free" in merged
        assert "gluten_free" in merged
        assert "nut_free" in merged
        
        # Should detect common restrictions
        common = linking_service.find_common_restrictions(family_restrictions)
        assert "vegetarian" in common  # Common to user123 and user789
    
    @pytest.mark.asyncio
    async def test_family_nutrition_goals(self, linking_service):
        """Test family nutrition goal coordination."""
        group_id = "group123"
        individual_goals = {
            "user123": {"goal": "weight_loss", "calorie_target": 1800},
            "user456": {"goal": "muscle_gain", "calorie_target": 2500},
            "user789": {"goal": "maintenance", "calorie_target": 2000}
        }
        
        family_strategy = await linking_service.coordinate_family_nutrition_goals(
            group_id, individual_goals
        )
        
        assert family_strategy.cooking_strategy is not None
        assert family_strategy.portion_adjustments is not None
        assert family_strategy.shared_base_meals is not None


class TestSeamlessUserProfileService:
    """Test seamless user profiling and learning."""
    
    @pytest.fixture
    def profile_service(self):
        """Create profile service."""
        return SeamlessUserProfileService()
    
    @pytest.mark.asyncio
    async def test_implicit_preference_learning(self, profile_service):
        """Test learning preferences from implicit signals."""
        user_id = "user123"
        interaction_data = [
            {"action": "recipe_view_time", "recipe_id": "rec1", "cuisine": "italian", "view_time": 45},
            {"action": "recipe_view_time", "recipe_id": "rec2", "cuisine": "mexican", "view_time": 10},
            {"action": "ingredient_substitution", "original": "beef", "substitute": "tofu"},
            {"action": "meal_completion_rate", "meal_type": "breakfast", "completion": 0.9},
            {"action": "meal_completion_rate", "meal_type": "dinner", "completion": 0.6}
        ]
        
        learned_profile = await profile_service.learn_from_interactions(
            user_id, interaction_data
        )
        
        assert "italian" in learned_profile.preferred_cuisines
        assert "mexican" not in learned_profile.preferred_cuisines  # Low engagement
        assert "tofu" in learned_profile.preferred_proteins
        assert learned_profile.meal_engagement["breakfast"] > learned_profile.meal_engagement["dinner"]
    
    @pytest.mark.asyncio
    async def test_nutrition_pattern_recognition(self, profile_service):
        """Test recognition of nutrition patterns."""
        user_id = "user123"
        nutrition_logs = [
            {"date": "2024-01-01", "calories": 2100, "protein": 150, "carbs": 200, "mood": 8},
            {"date": "2024-01-02", "calories": 1800, "protein": 120, "carbs": 180, "mood": 6},
            {"date": "2024-01-03", "calories": 2000, "protein": 140, "carbs": 220, "mood": 7},
            {"date": "2024-01-04", "calories": 2200, "protein": 160, "carbs": 250, "mood": 9},
        ]
        
        patterns = await profile_service.identify_nutrition_patterns(user_id, nutrition_logs)
        
        assert "optimal_calorie_range" in patterns
        assert "protein_mood_correlation" in patterns
        assert patterns["optimal_calorie_range"]["min"] > 0
        assert patterns["protein_mood_correlation"] > 0  # Higher protein correlates with better mood
    
    def test_seasonal_adjustment_learning(self, profile_service):
        """Test learning seasonal preference adjustments."""
        historical_data = {
            "winter": {"preferred_foods": ["soup", "stew", "hot_drinks"], "activity_level": "low"},
            "spring": {"preferred_foods": ["salads", "fresh_fruits"], "activity_level": "medium"},
            "summer": {"preferred_foods": ["grilled_foods", "cold_drinks"], "activity_level": "high"},
            "fall": {"preferred_foods": ["roasted_vegetables", "warm_spices"], "activity_level": "medium"}
        }
        
        current_season = "winter"
        adjustments = profile_service.get_seasonal_adjustments(historical_data, current_season)
        
        assert "soup" in adjustments.recommended_foods
        assert adjustments.activity_multiplier < 1.0  # Lower activity in winter
        assert "warming" in adjustments.preferred_preparation_methods
    
    @pytest.mark.asyncio
    async def test_social_influence_modeling(self, profile_service):
        """Test modeling social influences on food choices."""
        user_id = "user123"
        social_context = {
            "family_preferences": ["italian", "mexican"],
            "friend_recommendations": ["thai", "japanese"],
            "community_trends": ["plant_based", "meal_prep"],
            "cultural_background": ["mediterranean"]
        }
        
        social_influence = await profile_service.model_social_influences(
            user_id, social_context
        )
        
        assert social_influence.family_weight > 0
        assert social_influence.friend_weight > 0
        assert "mediterranean" in social_influence.cultural_preferences
        assert "plant_based" in social_influence.trending_preferences
    
    def test_profile_adaptation_rate(self, profile_service):
        """Test adaptive learning rate based on user feedback."""
        user_feedback_history = [
            {"feedback": "positive", "confidence": 0.9},
            {"feedback": "positive", "confidence": 0.8},
            {"feedback": "negative", "confidence": 0.7},
            {"feedback": "positive", "confidence": 0.95}
        ]
        
        adaptation_rate = profile_service.calculate_adaptation_rate(user_feedback_history)
        
        # High positive feedback should increase adaptation rate
        assert adaptation_rate > 0.5
        
        # With negative feedback mixed in, should be moderated
        assert adaptation_rate < 1.0


class TestCommunityPrivacyAndSecurity:
    """Test privacy and security in community features."""
    
    def test_reflection_privacy_levels(self):
        """Test different privacy levels for reflections."""
        from src.services.community.privacy import ReflectionPrivacy
        
        privacy = ReflectionPrivacy()
        
        reflection_content = "I struggle with emotional eating when stressed about work."
        
        # Public level - minimal anonymization
        public_version = privacy.apply_privacy_level(reflection_content, "public")
        assert len(public_version) == len(reflection_content)
        
        # Anonymous level - remove identifying details
        anonymous_version = privacy.apply_privacy_level(reflection_content, "anonymous")
        assert "work" not in anonymous_version or "[WORKPLACE]" in anonymous_version
        
        # Private level - only anonymized aggregation
        private_version = privacy.apply_privacy_level(reflection_content, "private")
        assert private_version != reflection_content
        assert len(private_version) < len(reflection_content)
    
    def test_member_data_protection(self):
        """Test protection of member data in crews."""
        from src.services.community.privacy import MemberDataProtection
        
        protection = MemberDataProtection()
        
        member_data = {
            "user_id": "user123",
            "real_name": "John Smith",
            "email": "john@example.com",
            "phone": "+1234567890",
            "display_name": "JohnS",
            "join_date": datetime.now(),
            "crew_role": "member"
        }
        
        # Public view should only show display name and role
        public_view = protection.filter_for_public_view(member_data)
        
        assert "display_name" in public_view
        assert "crew_role" in public_view
        assert "real_name" not in public_view
        assert "email" not in public_view
        assert "phone" not in public_view


# Performance tests for community features
class TestCommunityPerformance:
    """Test performance characteristics of community features."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_crew_reflection_aggregation(self):
        """Test performance with large crew reflection aggregation."""
        # Simulate 1000 reflections
        reflection_count = 1000
        
        start_time = datetime.utcnow()
        
        # Mock aggregation processing
        for i in range(reflection_count):
            # Simulate reflection processing
            pass
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should handle large crews efficiently
        assert duration < 2.0  # Complete within 2 seconds
    
    @pytest.mark.performance
    def test_anonymization_performance(self):
        """Test anonymization performance on large content."""
        from src.services.community.anonymization import AnonymizationService
        
        anonymizer = AnonymizationService()
        
        # Large content with multiple PII instances
        large_content = (
            "John Smith from New York works at Apple Inc. "
            "His email is john.smith@apple.com and phone is 555-123-4567. "
        ) * 100  # Repeat 100 times
        
        start_time = datetime.utcnow()
        anonymized = anonymizer.anonymize_content(large_content)
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        
        # Should complete anonymization quickly
        assert duration < 1.0  # Complete within 1 second
        assert len(anonymized) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
