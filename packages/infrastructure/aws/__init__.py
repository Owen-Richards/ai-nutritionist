"""AWS infrastructure package.

AWS-specific infrastructure implementations and adapters.
"""

from .dynamodb import DynamoDBClient, DynamoDBRepository
from .s3 import S3Client, S3Storage
from .lambda_handler import LambdaHandler, LambdaContext
from .bedrock import BedrockClient, AIService
from .pinpoint import PinpointClient, MessagingService

__all__ = [
    "DynamoDBClient",
    "DynamoDBRepository",
    "S3Client", 
    "S3Storage",
    "LambdaHandler",
    "LambdaContext",
    "BedrockClient",
    "AIService",
    "PinpointClient",
    "MessagingService",
]
