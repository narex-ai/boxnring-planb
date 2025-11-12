"""
Configuration management for Glovy AI Agent backend.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: Optional[str] = None
    
    # Gemini Configuration
    google_api_key: str
    google_model: str = "gemini-1.5-flash"
    
    # Mem0 Configuration
    mem0_api_key: Optional[str] = None
    
    # Glovy Configuration
    glovy_persona: str = "glovy"
    glovy_response_threshold: float = 0.7  # Tone threshold for responding
    glovy_min_messages_before_response: int = 2
    glovy_response_model: str = "gemini-1.5-flash"  # Model for response generation
    
    # Environment
    environment: str = "development"
    
    # FastAPI Configuration (Optional)
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


