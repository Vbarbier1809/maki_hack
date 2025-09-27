#!/usr/bin/env python3
"""
Quick Start Script - Handles port conflicts automatically
"""

import os
import subprocess
import sys
import time

def main():
    print("🚀 Quick Start - Voice Questionnaire")
    print("=" * 40)
    
    # Kill any process using port 5001
    print("🔍 Checking for port conflicts...")
    try:
        result = subprocess.run(['lsof', '-ti:5001'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"⚠️  Found {len(pids)} process(es) using port 5001 - killing them...")
            for pid in pids:
                if pid.strip():
                    subprocess.run(['kill', '-9', pid], check=False)
            time.sleep(1)
            print("✅ Port 5001 freed!")
        else:
            print("✅ Port 5001 is free")
    except:
        print("✅ Port check completed")
    
    # Clean up old files
    print("\n🧹 Cleaning up old files...")
    import glob
    old_files = glob.glob("responses/answers_*.json") + glob.glob("completed_questions_*.json")
    for file_path in old_files:
        try:
            os.remove(file_path)
            print(f"🗑️  Removed: {file_path}")
        except:
            pass
    print("✅ Cleanup completed!")
    
    # Start application
    print("\n🌐 Starting application on http://localhost:5001")
    print("🎤 Make sure your microphone and speakers are working!")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
