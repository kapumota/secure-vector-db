class SecureVectorDBError(Exception):
    """Base exception for controlled application errors."""

class ValidationError(SecureVectorDBError):
    """Raised when user input is invalid."""

class RecordNotFoundError(SecureVectorDBError):
    """Raised when a record does not exist."""

class StorageError(SecureVectorDBError):
    """Raised when durable storage cannot be read or written."""

class IntegrityError(SecureVectorDBError):
    """Raised when persisted integrity metadata is invalid or tampered."""
