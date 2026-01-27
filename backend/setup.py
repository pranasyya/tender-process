#!/usr/bin/env python3
"""Setup script for TenderGPT"""
import os
import subprocess
import sys

def check_requirements():
    """Check and install requirements"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False
    return True

def create_directories():
    """Create necessary directories"""
    dirs = [
        "outputs/uploads",
        "outputs/extractions",
        "app/assets"
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ Created directory: {dir_path}")
    
    return True

def create_env_template():
    """Create .env template if it doesn't exist"""
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("""# TenderGPT Configuration
OPENAI_API_KEY=your_openai_key_here
AZURE_API_KEY=your_azure_key_here
AZURE_ENDPOINT=your_azure_endpoint_here
AZURE_API_VERSION=2024-02-01
AZURE_DEPLOYMENT_MODEL=gpt-4
AZURE_DEPLOYMENT_NAME=your_deployment_name
PROVIDER=azure
""")
        print("✓ Created .env template")
        print("⚠️  Please edit .env file with your API keys")
    return True

def main():
    """Main setup function"""
    print("Setting up TenderGPT...")
    
    steps = [
        ("Installing requirements", check_requirements),
        ("Creating directories", create_directories),
        ("Creating environment file", create_env_template),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"✗ {step_name} failed")
            return False
        print(f"✓ {step_name} completed")
    
    print("\n" + "="*50)
    print("✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python run.py")
    print("="*50)
    return True

if __name__ == "__main__":
    main()