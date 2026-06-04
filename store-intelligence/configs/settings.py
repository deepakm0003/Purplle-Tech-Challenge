"""
Application Settings Module

This module defines all application configuration using Pydantic Settings v2.
Settings are loaded from environment variables with validation and type conversion.

All settings are lazy-loaded as singletons, ensuring consistent configuration
across the entire application lifecycle.
"""

from typing import Optional
from functools import lru_cache

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.
    
    All settings are immutable after loading, ensuring configuration consistency.
    Type hints are enforced at load time using Pydantic v2.
    """

    # ============================================================================
    # Application Metadata
    # ============================================================================
    app_name: str = Field(default="Store Intelligence System", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")

    # ============================================================================
    # API Configuration
    # ============================================================================
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port", ge=1, le=65535)
    api_workers: int = Field(default=4, description="Number of Uvicorn workers", ge=1)
    api_reload: bool = Field(default=False, description="Enable auto-reload on code changes")

    # ============================================================================
    # Database Configuration (PostgreSQL + SQLAlchemy)
    # ============================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/store_intelligence",
        description="Async PostgreSQL connection URL"
    )
    database_echo: bool = Field(default=False, description="Echo SQL statements to logs")
    database_pool_size: int = Field(default=20, description="SQLAlchemy connection pool size", ge=5)
    database_max_overflow: int = Field(default=40, description="SQLAlchemy max overflow connections", ge=10)
    database_pool_pre_ping: bool = Field(default=True, description="Test connections before using them")
    database_pool_recycle: int = Field(default=3600, description="Recycle connections after N seconds", ge=300)

    # ============================================================================
    # Redis Configuration (Cache & Pub/Sub)
    # ============================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_decode_responses: bool = Field(default=True, description="Decode Redis responses to strings")
    redis_socket_connect_timeout: int = Field(default=5, description="Redis socket connect timeout (seconds)", ge=1)
    redis_socket_keepalive: bool = Field(default=True, description="Enable Redis socket keepalive")

    # ============================================================================
    # Security Configuration
    # ============================================================================
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT and password hashing (min 32 chars in prod)",
        min_length=8
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="JWT token expiry time (minutes)", ge=5)

    # ============================================================================
    # Logging Configuration
    # ============================================================================
    log_format: str = Field(default="json", description="Log format: json or text")
    log_dir: str = Field(default="logs", description="Directory for log files")
    log_file: str = Field(default="app.log", description="Main log file name")
    log_max_bytes: int = Field(default=10485760, description="Max log file size before rotation (bytes)")
    log_backup_count: int = Field(default=10, description="Number of rotated log files to keep")

    # ============================================================================
    # Detection Pipeline Configuration
    # ============================================================================
    detector_model_size: str = Field(
        default="nano",
        description="YOLOv8 model size: nano, small, medium, large"
    )
    detector_confidence_threshold: float = Field(
        default=0.4,
        description="Confidence threshold for person detections",
        ge=0.1,
        le=0.9
    )
    detector_nms_threshold: float = Field(
        default=0.5,
        description="Non-Maximum Suppression threshold",
        ge=0.3,
        le=0.9
    )
    detector_max_workers: int = Field(
        default=2,
        description="Max parallel detection workers",
        ge=1,
        le=8
    )
    motion_threshold: float = Field(
        default=0.05,
        description="Motion detection threshold (0-1 normalized)",
        ge=0.01,
        le=0.2
    )
    base_skip_frames: int = Field(
        default=3,
        description="Skip frames at rest (every Nth frame processed)",
        ge=1,
        le=10
    )
    active_skip_frames: int = Field(
        default=1,
        description="Skip frames during motion (every Nth frame processed)",
        ge=1,
        le=5
    )

    # ============================================================================
    # Tracking Configuration (DeepSORT)
    # ============================================================================
    tracker_max_age: int = Field(
        default=30,
        description="Max frames to keep track alive without detection",
        ge=5,
        le=100
    )
    tracker_min_hits: int = Field(
        default=3,
        description="Min detections to confirm a new track",
        ge=1,
        le=10
    )
    tracker_iou_threshold: float = Field(
        default=0.3,
        description="IOU threshold for track matching",
        ge=0.1,
        le=0.7
    )

    # ============================================================================
    # Zone Configuration
    # ============================================================================
    zone_config_path: str = Field(
        default="./config/zones.json",
        description="Path to zone definitions JSON file"
    )

    # ============================================================================
    # Analytics Configuration
    # ============================================================================
    anomaly_detection_enabled: bool = Field(default=True, description="Enable anomaly detection")
    queue_depth_window_seconds: int = Field(
        default=30,
        description="Window for queue depth calculation",
        ge=10,
        le=300
    )
    anomaly_check_interval_seconds: int = Field(
        default=60,
        description="Interval between anomaly checks",
        ge=10,
        le=300
    )
    isolation_forest_contamination: float = Field(
        default=0.05,
        description="Expected proportion of anomalies (0-1)",
        ge=0.01,
        le=0.5
    )

    # ============================================================================
    # Kafka Configuration (for streaming events)
    # ============================================================================
    kafka_bootstrap_servers: str = Field(
        default="kafka:9092",
        description="Kafka bootstrap servers"
    )
    kafka_topic_detections: str = Field(default="raw_detections", description="Topic for raw detections")
    kafka_topic_tracking: str = Field(default="tracking_events", description="Topic for tracking events")
    kafka_topic_zones: str = Field(default="zone_events", description="Topic for zone events")
    kafka_topic_anomalies: str = Field(default="anomalies", description="Topic for anomalies")
    kafka_consumer_group: str = Field(default="analytics_group", description="Kafka consumer group")

    # ============================================================================
    # Store Configuration
    # ============================================================================
    default_store_id: str = Field(
        default="STORE-BLR-01",
        description="Default store ID for initialization"
    )
    default_camera_id: str = Field(
        default="CAM-ENTRY-01",
        description="Default camera ID for initialization"
    )
    brigade_csv_path: Optional[str] = Field(
        default=None,
        description="Path to Brigade Bangalore POS CSV (Purplle submission data)",
    )
    brigade_cctv_dir: Optional[str] = Field(
        default=None,
        description="Path to Brigade CCTV footage folder (5 MP4 files)",
    )

    # ============================================================================
    # CORS Configuration
    # ============================================================================
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_allow_methods: list[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_allow_headers: list[str] = Field(default=["*"], description="Allowed CORS headers")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=True,
        populate_by_name=True,
    )

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate app environment is one of allowed values."""
        allowed_envs = ["development", "staging", "production"]
        if v.lower() not in allowed_envs:
            raise ValueError(f"app_env must be one of {allowed_envs}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid Python logging level."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"log_level must be one of {allowed_levels}")
        return v.upper()

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format is one of allowed values."""
        allowed_formats = ["json", "text"]
        if v.lower() not in allowed_formats:
            raise ValueError(f"log_format must be one of {allowed_formats}")
        return v.lower()

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate secret key length in production."""
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters in production")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings singleton.
    
    This function returns a cached instance of Settings, ensuring that
    environment variables are only parsed once during application startup.
    
    Returns:
        Settings: Validated settings instance
        
    Example:
        ```python
        from configs import get_settings
        
        settings = get_settings()
        print(settings.database_url)
        ```
    """
    return Settings()
