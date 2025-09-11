#!/usr/bin/env python3
"""
🌍 Africa Network Infrastructure Optimizer - Startup Script
Quick launcher for the Flask application
"""

import os
import sys
import subprocess
import platform

def main():
    print("🚀 Starting Africa Network Infrastructure Optimizer...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("routing_optimizer"):
        print("❌ Error: routing_optimizer directory not found")
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    # Navigate to the application directory
    os.chdir("routing_optimizer")
    
    # Check if requirements are installed
    print("📦 Checking dependencies...")
    try:
        import flask
        print("✅ Dependencies already installed")
    except ImportError:
        print("📥 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Start the application
    print("🌍 Starting the application...")
    print("=" * 50)
    print("🔗 The application will be available at: http://localhost:5000")
    if platform.system() != "Windows":
        print("🔗 In Codespaces, access through the forwarded port")
    print("=" * 50)
    
    # Run the Flask application
    try:
        subprocess.run([sys.executable, "run_app.py"])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

if __name__ == "__main__":
    main()
