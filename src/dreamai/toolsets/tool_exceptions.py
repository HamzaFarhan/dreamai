"""
Common exception classes for FP&A operations.

This module provides a standardized exception hierarchy that can be used
across all FP&A tools and functions to ensure consistent error handling
for AI agent integration.
"""


class FPABaseException(Exception):
    """Base exception for FP&A operations"""

    pass


class RetryAfterCorrectionError(FPABaseException):
    """Error that can be resolved by correcting input data or parameters"""

    def __init__(self, message: str, correction_hint: str):
        self.correction_hint = correction_hint
        super().__init__(message)


class ValidationError(FPABaseException):
    """Input validation failed - data structure or business rule violation"""

    pass


class CalculationError(FPABaseException):
    """Mathematical or financial calculation error - likely data issue"""

    pass


class ConfigurationError(FPABaseException):
    """Function configuration or parameter error - code issue"""

    pass


class DataQualityError(RetryAfterCorrectionError):
    """Data quality issues that can be corrected"""

    pass
