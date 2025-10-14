"""Comprehensive Pydantic models for user management and profiles."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr, ConfigDict


class GenderType(str, Enum):
    """Gender types for user profiles."""
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class ActivityLevel(str, Enum):
    """Physical activity levels."""
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"


class DietaryRestriction(str, Enum):
    """Dietary restrictions and preferences."""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    PESCATARIAN = "pescatarian"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    NUT_FREE = "nut_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    LOW_FAT = "low_fat"
    HIGH_PROTEIN = "high_protein"
    MEDITERRANEAN = "mediterranean"
    WHOLE30 = "whole30"
    INTERMITTENT_FASTING = "intermittent_fasting"


class HealthGoal(str, Enum):
    """Health and fitness goals."""
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    IMPROVED_ENERGY = "improved_energy"
    BETTER_DIGESTION = "better_digestion"
    HEART_HEALTH = "heart_health"
    DIABETES_MANAGEMENT = "diabetes_management"
    SPORTS_PERFORMANCE = "sports_performance"
    GENERAL_WELLNESS = "general_wellness"


class AllergySeverity(str, Enum):
    """Allergy severity levels."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    ANAPHYLACTIC = "anaphylactic"


class BaseValidationModel(BaseModel):
    """Base model with comprehensive validation."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        extra='forbid',
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            UUID: lambda v: str(v) if v else None,
            Decimal: lambda v: float(v) if v else None,
        }
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the model was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the model was last updated"
    )


class UserAllergy(BaseValidationModel):
    """User allergy information with severity and notes."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique allergy identifier")
    allergen: Annotated[str, Field(min_length=1, max_length=100)] = Field(
        ...,
        description="Name of the allergen"
    )
    severity: AllergySeverity = Field(
        ...,
        description="Severity level of the allergy"
    )
    notes: Optional[Annotated[str, Field(max_length=500)]] = Field(
        None,
        description="Additional notes about the allergy"
    )
    diagnosed_date: Optional[date] = Field(
        None,
        description="Date when allergy was diagnosed"
    )
    verified_by_doctor: bool = Field(
        default=False,
        description="Whether allergy has been verified by a healthcare professional"
    )


class UserHealthMetrics(BaseValidationModel):
    """User health metrics and measurements."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique metrics identifier")
    weight_kg: Optional[Annotated[float, Field(gt=0, le=1000)]] = Field(
        None,
        description="Weight in kilograms"
    )
    height_cm: Optional[Annotated[float, Field(gt=0, le=300)]] = Field(
        None,
        description="Height in centimeters"
    )
    bmi: Optional[Annotated[float, Field(gt=0, le=100)]] = Field(
        None,
        description="Body Mass Index"
    )
    body_fat_percentage: Optional[Annotated[float, Field(ge=0, le=100)]] = Field(
        None,
        description="Body fat percentage"
    )
    muscle_mass_kg: Optional[Annotated[float, Field(gt=0, le=200)]] = Field(
        None,
        description="Muscle mass in kilograms"
    )
    resting_heart_rate: Optional[Annotated[int, Field(gt=0, le=200)]] = Field(
        None,
        description="Resting heart rate in beats per minute"
    )
    blood_pressure_systolic: Optional[Annotated[int, Field(gt=0, le=300)]] = Field(
        None,
        description="Systolic blood pressure in mmHg"
    )
    blood_pressure_diastolic: Optional[Annotated[int, Field(gt=0, le=200)]] = Field(
        None,
        description="Diastolic blood pressure in mmHg"
    )
    
    @model_validator(mode='after')
    def validate_health_metrics_consistency(self) -> 'UserHealthMetrics':
        """Validate consistency between health metrics."""
        # Validate BMI consistency with weight and height
        if self.weight_kg and self.height_cm and self.bmi:
            calculated_bmi = self.weight_kg / ((self.height_cm / 100) ** 2)
            if abs(calculated_bmi - self.bmi) > 1.0:
                raise ValueError("BMI is inconsistent with weight and height")
        
        # Validate blood pressure consistency
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            if self.blood_pressure_systolic <= self.blood_pressure_diastolic:
                raise ValueError("Systolic pressure must be higher than diastolic pressure")
        
        return self


class UserPreferences(BaseValidationModel):
    """User dietary and lifestyle preferences."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique preferences identifier")
    dietary_restrictions: List[DietaryRestriction] = Field(
        default_factory=list,
        description="List of dietary restrictions and preferences"
    )
    health_goals: List[HealthGoal] = Field(
        default_factory=list,
        description="List of health and fitness goals"
    )
    allergies: List[UserAllergy] = Field(
        default_factory=list,
        description="List of food allergies"
    )
    disliked_foods: List[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list,
        description="List of disliked foods to avoid"
    )
    favorite_foods: List[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list,
        description="List of favorite foods to include"
    )
    cuisine_preferences: List[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list,
        description="Preferred cuisine types"
    )
    cooking_time_preference: Optional[Annotated[int, Field(gt=0, le=300)]] = Field(
        None,
        description="Preferred cooking time in minutes"
    )
    budget_per_meal: Optional[Annotated[Decimal, Field(gt=0, le=1000)]] = Field(
        None,
        description="Budget per meal in USD"
    )
    meal_frequency: Optional[Annotated[int, Field(gt=0, le=10)]] = Field(
        None,
        description="Number of meals per day"
    )
    
    @field_validator('dietary_restrictions')
    @classmethod
    def validate_dietary_restrictions(cls, v: List[DietaryRestriction]) -> List[DietaryRestriction]:
        """Validate dietary restriction combinations."""
        if not v:
            return v
        
        # Check for conflicting restrictions
        conflicts = [
            ([DietaryRestriction.VEGETARIAN, DietaryRestriction.VEGAN], 
             "Cannot be both vegetarian and vegan"),
            ([DietaryRestriction.KETO, DietaryRestriction.LOW_FAT], 
             "Keto and low-fat diets are conflicting"),
        ]
        
        for conflict_set, message in conflicts:
            if all(restriction in v for restriction in conflict_set):
                raise ValueError(message)
        
        return v


class UserProfile(BaseValidationModel):
    """Complete user profile with personal information and preferences."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique user identifier")
    
    # Personal Information
    first_name: Annotated[str, Field(min_length=1, max_length=50)] = Field(
        ...,
        description="User's first name"
    )
    last_name: Annotated[str, Field(min_length=1, max_length=50)] = Field(
        ...,
        description="User's last name"
    )
    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    phone_number: Optional[Annotated[str, Field(pattern=r'^\+?1?\d{9,15}$')]] = Field(
        None,
        description="User's phone number"
    )
    birth_date: Optional[date] = Field(
        None,
        description="User's birth date"
    )
    gender: Optional[GenderType] = Field(
        None,
        description="User's gender"
    )
    
    # Health Information
    health_metrics: Optional[UserHealthMetrics] = Field(
        None,
        description="User's health metrics"
    )
    activity_level: Optional[ActivityLevel] = Field(
        None,
        description="User's physical activity level"
    )
    
    # Preferences
    preferences: Optional[UserPreferences] = Field(
        None,
        description="User's dietary and lifestyle preferences"
    )
    
    # Account Settings
    timezone: Annotated[str, Field(max_length=50)] = Field(
        default="UTC",
        description="User's timezone"
    )
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email_notifications": True,
            "push_notifications": True,
            "meal_reminders": True,
            "progress_updates": False
        },
        description="User's notification preferences"
    )
    privacy_settings: Dict[str, bool] = Field(
        default_factory=lambda: {
            "profile_public": False,
            "share_progress": False,
            "data_collection_consent": True
        },
        description="User's privacy settings"
    )
    
    @field_validator('birth_date')
    @classmethod
    def validate_birth_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate birth date is reasonable."""
        if v is None:
            return v
        
        today = date.today()
        if v > today:
            raise ValueError("Birth date cannot be in the future")
        
        age = (today - v).days // 365
        if age > 120:
            raise ValueError("Age cannot exceed 120 years")
        if age < 13:
            raise ValueError("User must be at least 13 years old")
        
        return v
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate and format phone number."""
        if v is None:
            return v
        
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
        
        if not cleaned:
            raise ValueError("Phone number must contain digits")
        
        # Basic validation
        if cleaned.startswith('+'):
            if len(cleaned) < 8 or len(cleaned) > 16:
                raise ValueError("International phone number must be 8-16 digits including country code")
        else:
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValueError("Phone number must be 7-15 digits")
        
        return cleaned
    
    @property
    def age(self) -> Optional[int]:
        """Calculate user's age from birth date."""
        if self.birth_date is None:
            return None
        
        today = date.today()
        return (today - self.birth_date).days // 365
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"


# API Request/Response Models

class APIBaseModel(BaseModel):
    """Base model for API requests and responses."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        extra='forbid'
    )


class UserRegistrationRequest(APIBaseModel):
    """Request model for user registration."""
    
    first_name: Annotated[str, Field(min_length=1, max_length=50)] = Field(
        ...,
        description="User's first name"
    )
    last_name: Annotated[str, Field(min_length=1, max_length=50)] = Field(
        ...,
        description="User's last name"
    )
    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    password: Annotated[str, Field(min_length=8, max_length=128)] = Field(
        ...,
        description="User's password"
    )
    terms_accepted: bool = Field(
        ...,
        description="Whether user has accepted terms of service"
    )
    privacy_policy_accepted: bool = Field(
        ...,
        description="Whether user has accepted privacy policy"
    )
    marketing_consent: bool = Field(
        default=False,
        description="Whether user consents to marketing communications"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for required character types
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*(),.?":{}|<>' for c in v)
        
        requirements_met = sum([has_upper, has_lower, has_digit, has_special])
        if requirements_met < 3:
            raise ValueError("Password must contain at least 3 of: uppercase, lowercase, digits, special characters")
        
        return v
    
    @field_validator('terms_accepted', 'privacy_policy_accepted')
    @classmethod
    def validate_required_consents(cls, v: bool) -> bool:
        """Validate required consents are accepted."""
        if not v:
            raise ValueError("Required consent must be accepted")
        return v


class UserUpdateRequest(APIBaseModel):
    """Request model for user profile updates."""
    
    first_name: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = None
    last_name: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = None
    phone_number: Optional[Annotated[str, Field(pattern=r'^\+?1?\d{9,15}$')]] = None
    birth_date: Optional[date] = None
    gender: Optional[GenderType] = None
    timezone: Optional[Annotated[str, Field(max_length=50)]] = None
    notification_preferences: Optional[Dict[str, bool]] = None
    privacy_settings: Optional[Dict[str, bool]] = None


class UserHealthMetricsUpdateRequest(APIBaseModel):
    """Request model for updating user health metrics."""
    
    weight_kg: Optional[Annotated[float, Field(gt=0, le=1000)]] = None
    height_cm: Optional[Annotated[float, Field(gt=0, le=300)]] = None
    body_fat_percentage: Optional[Annotated[float, Field(ge=0, le=100)]] = None
    muscle_mass_kg: Optional[Annotated[float, Field(gt=0, le=200)]] = None
    resting_heart_rate: Optional[Annotated[int, Field(gt=0, le=200)]] = None
    blood_pressure_systolic: Optional[Annotated[int, Field(gt=0, le=300)]] = None
    blood_pressure_diastolic: Optional[Annotated[int, Field(gt=0, le=200)]] = None


class UserPreferencesUpdateRequest(APIBaseModel):
    """Request model for updating user preferences."""
    
    dietary_restrictions: Optional[List[DietaryRestriction]] = None
    health_goals: Optional[List[HealthGoal]] = None
    allergies: Optional[List[UserAllergy]] = None
    disliked_foods: Optional[List[Annotated[str, Field(min_length=1, max_length=100)]]] = None
    favorite_foods: Optional[List[Annotated[str, Field(min_length=1, max_length=100)]]] = None
    cuisine_preferences: Optional[List[Annotated[str, Field(min_length=1, max_length=50)]]] = None
    cooking_time_preference: Optional[Annotated[int, Field(gt=0, le=300)]] = None
    budget_per_meal: Optional[Annotated[Decimal, Field(gt=0, le=1000)]] = None
    meal_frequency: Optional[Annotated[int, Field(gt=0, le=10)]] = None


class UserProfileResponse(APIBaseModel):
    """Response model for user profile data."""
    
    user: UserProfile = Field(
        ...,
        description="Complete user profile information"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracing"
    )


class UserListResponse(APIBaseModel):
    """Response model for user list operations."""
    
    users: List[UserProfile] = Field(
        ...,
        description="List of user profiles"
    )
    total_count: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total number of users"
    )
    page: Annotated[int, Field(gt=0)] = Field(
        ...,
        description="Current page number"
    )
    page_size: Annotated[int, Field(gt=0, le=100)] = Field(
        ...,
        description="Number of items per page"
    )


class UserStatsResponse(APIBaseModel):
    """Response model for user statistics."""
    
    total_users: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total number of registered users"
    )
    active_users_last_30_days: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Number of active users in the last 30 days"
    )
    new_registrations_last_7_days: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="New user registrations in the last 7 days"
    )
    average_age: Optional[Annotated[float, Field(gt=0, le=120)]] = Field(
        None,
        description="Average age of users"
    )
    gender_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of users by gender"
    )
    top_dietary_restrictions: List[Dict[str, Union[str, int]]] = Field(
        default_factory=list,
        description="Most common dietary restrictions"
    )
    top_health_goals: List[Dict[str, Union[str, int]]] = Field(
        default_factory=list,
        description="Most common health goals"
    )
