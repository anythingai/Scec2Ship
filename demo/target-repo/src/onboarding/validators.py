from typing import Dict, Callable, NamedTuple
from src.utils.system_checks import check_database_connection, check_api_key_presence, check_config_file_syntax

class ValidationResult(NamedTuple):
    success: bool
    message: str

def validate_db() -> ValidationResult:
    success = check_database_connection()
    return ValidationResult(success, "Database connected" if success else "Database connection failed")

def validate_api_key() -> ValidationResult:
    success = check_api_key_presence()
    return ValidationResult(success, "API Key found" if success else "API Key missing")

def validate_config() -> ValidationResult:
    success = check_config_file_syntax()
    return ValidationResult(success, "Config valid" if success else "Config invalid")

# Map item IDs to validators
VALIDATORS: Dict[str, Callable[[], ValidationResult]] = {
    "db_check": validate_db,
    "api_key_check": validate_api_key,
    "config_check": validate_config,
}
