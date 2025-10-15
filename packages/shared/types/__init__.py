"""Shared types package.

Common types and data structures used across domains.
"""

from .common import (
    UUID, DateTime, Date, Decimal,
    JSONPrimitive, JSONValue, JSONDict, JSONList,
    T, U, V, TUser, TMeal, TPlan, TEvent, TComparable,
    Numeric, PositiveInt, NonNegativeInt, PositiveFloat, NonNegativeFloat,
    NonEmptyStr, EmailStr, PhoneStr, URLStr,
    UserID, PlanID, MealID, CrewID, ReflectionID, EventID, SessionID, RequestID,
    Percentage, Rate,
    Comparable, Hashable, Serializable, Identifiable, Timestamped, Versioned,
    ConfigValue, ConfigDict,
    ErrorCode, ErrorMessage, ErrorDetails,
    PageSize, PageNumber, TotalCount, Offset, Limit,
    Token, RefreshToken, APIKey, Secret,
    HTTPMethod, HTTPStatus, HTTPHeaders, QueryParams,
    FilePath, FileName, FileContent, FileSize, MimeType,
    Latitude, Longitude, Coordinates,
    Currency, MoneyAmount, Price, Cost, Budget,
    CalorieCount, MacroGrams, Protein, Carbs, Fat, Fiber, Sugar, Sodium,
    Duration, Minutes, Hours, Days, Weeks,
    Rating, Score, Confidence,
    StringList, StringSet, StringDict, IntList, FloatList,
    OptionalStr, OptionalInt, OptionalFloat, OptionalBool, OptionalDateTime, OptionalUUID,
    is_non_empty_string, is_positive_number, is_valid_email, is_valid_phone, is_valid_uuid, is_percentage, is_rate
)

from .result import (
    Result, Success, Failure,
    AppError, ValidationError as ResultValidationError, NotFoundError, ConflictError,
    AuthenticationError, AuthorizationError, RateLimitError, ExternalServiceError,
    success, failure, from_optional, from_exception, collect_results,
    StrResult, IntResult, BoolResult, DictResult, ListResult, VoidResult
)

from .pagination import (
    Sort, Pagination, PageInfo, Page,
    Cursor, CursorPagination, CursorPage,
    validate_pagination, validate_cursor_pagination,
    SortDirection, StringPage, IntPage, DictPage,
    StringCursorPage, IntCursorPage, DictCursorPage
)

from .validation import (
    ValidationIssue, ValidationResult, ValidationError,
    Validator, FieldValidators, ValidationFunction,
    Validators, combine_validators, validate_field, validate_dict
)

from .literals import (
    # Authentication
    AuthChannel, TokenType, AuthStatus,
    # Subscriptions
    SubscriptionTier, SubscriptionStatus, BillingInterval,
    # Nutrition
    DietaryRestriction, CuisineType, GoalType, ActivityLevel,
    MealType, DayOfWeek, PrepTimePreference, CookingSkillLevel,
    CookingEquipment, ServingSize, Difficulty,
    # Community
    CrewType, ReflectionType, MoodScore,
    # Analytics
    EventType, ConsentType, MetricType,
    # Integrations
    CalendarProvider, FitnessProvider, GroceryPartner,
    CalendarEventType, ReminderType, WorkoutType, WorkoutIntensity,
    # Notifications
    NotificationType, NotificationPriority, NotificationChannel,
    # Health
    HealthMetric,
    # Files
    FileType, ImageFormat, DocumentFormat,
    # API
    APIVersion, ContentType,
    # Status
    TaskStatus, ProcessingStatus, SyncStatus,
    # Features
    FeatureFlag, ExperimentType, ExperimentStatus,
    # Errors
    ErrorSeverity, ErrorCategory, LogLevel,
    # Infrastructure
    Environment, Region, DataFormat, CompressionType, EncryptionType,
    # Internationalization
    TimeUnit, CurrencyCode, LanguageCode, CountryCode, TimezoneId,
    # Union types
    AnyRestriction, AnyCuisine, AnyGoal, AnyEquipment
)

__all__ = [
    # Common types
    "UUID", "DateTime", "Date", "Decimal",
    "JSONPrimitive", "JSONValue", "JSONDict", "JSONList",
    "T", "U", "V", "TUser", "TMeal", "TPlan", "TEvent", "TComparable",
    "Numeric", "PositiveInt", "NonNegativeInt", "PositiveFloat", "NonNegativeFloat",
    "NonEmptyStr", "EmailStr", "PhoneStr", "URLStr",
    "UserID", "PlanID", "MealID", "CrewID", "ReflectionID", "EventID", "SessionID", "RequestID",
    "Percentage", "Rate",
    "Comparable", "Hashable", "Serializable", "Identifiable", "Timestamped", "Versioned",
    "ConfigValue", "ConfigDict",
    "ErrorCode", "ErrorMessage", "ErrorDetails",
    "PageSize", "PageNumber", "TotalCount", "Offset", "Limit",
    "Token", "RefreshToken", "APIKey", "Secret",
    "HTTPMethod", "HTTPStatus", "HTTPHeaders", "QueryParams",
    "FilePath", "FileName", "FileContent", "FileSize", "MimeType",
    "Latitude", "Longitude", "Coordinates",
    "Currency", "MoneyAmount", "Price", "Cost", "Budget",
    "CalorieCount", "MacroGrams", "Protein", "Carbs", "Fat", "Fiber", "Sugar", "Sodium",
    "Duration", "Minutes", "Hours", "Days", "Weeks",
    "Rating", "Score", "Confidence",
    "StringList", "StringSet", "StringDict", "IntList", "FloatList",
    "OptionalStr", "OptionalInt", "OptionalFloat", "OptionalBool", "OptionalDateTime", "OptionalUUID",
    "is_non_empty_string", "is_positive_number", "is_valid_email", "is_valid_phone", "is_valid_uuid", "is_percentage", "is_rate",
    
    # Result types
    "Result", "Success", "Failure",
    "AppError", "ResultValidationError", "NotFoundError", "ConflictError",
    "AuthenticationError", "AuthorizationError", "RateLimitError", "ExternalServiceError",
    "success", "failure", "from_optional", "from_exception", "collect_results",
    "StrResult", "IntResult", "BoolResult", "DictResult", "ListResult", "VoidResult",
    
    # Pagination types
    "Sort", "Pagination", "PageInfo", "Page",
    "Cursor", "CursorPagination", "CursorPage",
    "validate_pagination", "validate_cursor_pagination",
    "SortDirection", "StringPage", "IntPage", "DictPage",
    "StringCursorPage", "IntCursorPage", "DictCursorPage",
    
    # Validation types
    "ValidationIssue", "ValidationResult", "ValidationError",
    "Validator", "FieldValidators", "ValidationFunction",
    "Validators", "combine_validators", "validate_field", "validate_dict",
    
    # Literal types
    "AuthChannel", "TokenType", "AuthStatus",
    "SubscriptionTier", "SubscriptionStatus", "BillingInterval",
    "DietaryRestriction", "CuisineType", "GoalType", "ActivityLevel",
    "MealType", "DayOfWeek", "PrepTimePreference", "CookingSkillLevel",
    "CookingEquipment", "ServingSize", "Difficulty",
    "CrewType", "ReflectionType", "MoodScore",
    "EventType", "ConsentType", "MetricType",
    "CalendarProvider", "FitnessProvider", "GroceryPartner",
    "CalendarEventType", "ReminderType", "WorkoutType", "WorkoutIntensity",
    "NotificationType", "NotificationPriority", "NotificationChannel",
    "HealthMetric",
    "FileType", "ImageFormat", "DocumentFormat",
    "APIVersion", "ContentType",
    "TaskStatus", "ProcessingStatus", "SyncStatus",
    "FeatureFlag", "ExperimentType", "ExperimentStatus",
    "ErrorSeverity", "ErrorCategory", "LogLevel",
    "Environment", "Region", "DataFormat", "CompressionType", "EncryptionType",
    "TimeUnit", "CurrencyCode", "LanguageCode", "CountryCode", "TimezoneId",
    "AnyRestriction", "AnyCuisine", "AnyGoal", "AnyEquipment",
]
