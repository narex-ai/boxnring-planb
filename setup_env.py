"""
Helper script to create .env file from template.
Run this to set up your environment variables.
"""
import os

def create_env_file():
    """Create .env file from user input."""
    print("Glovy Backend Setup")
    print("=" * 50)
    print("\nPlease provide the following information:\n")
    
    env_vars = {
        "SUPABASE_URL": input("Supabase URL: ").strip(),
        "SUPABASE_KEY": input("Supabase Anon Key: ").strip(),
        "SUPABASE_SERVICE_ROLE_KEY": input("Supabase Service Role Key (optional, press Enter to skip): ").strip() or "",
        "GOOGLE_API_KEY": input("Google Gemini API Key: ").strip(),
        "GOOGLE_MODEL": input("Gemini Model (default: gemini-2.5-flash): ").strip() or "gemini-2.5-flash",
        "MEM0_API_KEY": input("Mem0 API Key (optional, press Enter to skip): ").strip() or "",
        "GLOVY_PERSONA": input("Glovy Persona (default: glovy): ").strip() or "glovy",
        "GLOVY_RESPONSE_THRESHOLD": input("Response Threshold (0.0-1.0, default: 0.7): ").strip() or "0.7",
        "GLOVY_MIN_MESSAGES_BEFORE_RESPONSE": input("Min Messages Before Response (default: 2): ").strip() or "2",
        "GLOVY_RESPONSE_MODEL": input("Glovy Response Model (default: gemini-2.5-flash): ").strip() or "gemini-2.5-flash",
        "ENVIRONMENT": input("Environment (development/production, default: development): ").strip() or "development",
        "HOST": input("FastAPI Host (default: 0.0.0.0): ").strip() or "0.0.0.0",
        "PORT": input("FastAPI Port (default: 8000): ").strip() or "8000",
    }
    
    # Write to .env file
    env_content = "\n".join([f"{key}={value}" for key, value in env_vars.items() if value])
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n✓ .env file created successfully!")
    print("\nNext steps:")
    print("1. Review the .env file and make any necessary adjustments")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Start the backend:")
    print("   - FastAPI: python run.py")
    print("   - Legacy: python main.py")

if __name__ == "__main__":
    if os.path.exists(".env"):
        response = input(".env file already exists. Overwrite? (y/N): ").strip().lower()
        if response != "y":
            print("Cancelled.")
            exit(0)
    
    create_env_file()

