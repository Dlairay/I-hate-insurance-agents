#!/usr/bin/env python3
"""
AI Insurance Broker Demo Runner
================================
Complete system with MongoDB, questionnaire, and AI agents
"""

import subprocess
import sys
import time
import signal
from threading import Thread

class InsuranceDemo:
    def __init__(self):
        self.processes = []
        self.running = True
    
    def check_ollama(self):
        """Check if Ollama is running"""
        print("🤖 Checking Ollama...")
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                llama_models = [m for m in models if 'llama3' in m.get('name', '').lower()]
                if llama_models:
                    print(f"✅ Ollama running with {len(llama_models)} Llama3 model(s)")
                    return True
                else:
                    print("⚠️  Ollama running but no Llama3 model found")
                    print("🔄 Installing Llama3...")
                    subprocess.run(["ollama", "pull", "llama3:latest"], check=False)
                    return True
            return False
        except Exception as e:
            print(f"❌ Ollama not accessible: {e}")
            print("🚀 Please start Ollama manually:")
            print("   1. Install: brew install ollama")
            print("   2. Start: ollama serve")
            print("   3. Install model: ollama pull llama3:latest")
            print("   4. Then run this script again")
            return False

    def check_mongodb(self):
        """Check if MongoDB is running"""
        print("🍃 Checking MongoDB...")
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            client.server_info()
            print("✅ MongoDB is running")
            
            # Check if database has data
            db = client['insurance_db']
            companies = db['companies'].count_documents({})
            if companies == 0:
                print("📊 Database is empty, populating...")
                subprocess.run([sys.executable, "backend/populate_db.py"], check=True)
                print("✅ Database populated")
            else:
                print(f"✅ Database has {companies} companies")
            return True
        except Exception as e:
            print(f"❌ MongoDB not running: {e}")
            print("🚀 Starting MongoDB...")
            subprocess.run(["brew", "services", "start", "mongodb-community"], check=True)
            time.sleep(3)
            return self.check_mongodb()
    
    def start_backend(self):
        """Start insurance backend API"""
        print("🏥 Starting Insurance Backend API (port 8000)...")
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "backend.insurance_backend_mongo:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
        self.processes.append(("Backend API", process))
        return process
    
    def start_questionnaire(self):
        """Start questionnaire server"""
        print("📋 Starting Questionnaire Server (port 8001)...")
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "questionnaire.server:app",
            "--host", "0.0.0.0",
            "--port", "8001",
            "--reload"
        ])
        self.processes.append(("Questionnaire", process))
        return process
    
    def signal_handler(self, signum, frame):
        """Handle shutdown gracefully"""
        print("\n🛑 Shutting down services...")
        self.running = False
        for name, process in self.processes:
            print(f"   Stopping {name}...")
            process.terminate()
        time.sleep(2)
        for name, process in self.processes:
            if process.poll() is None:
                process.kill()
        print("👋 Demo stopped")
        sys.exit(0)
    
    def run(self):
        """Run the complete demo"""
        print("=" * 60)
        print("🚀 AI INSURANCE BROKER DEMO")
        print("=" * 60)
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check Ollama (for AI agents)
        ollama_running = self.check_ollama()
        if not ollama_running:
            print("⚠️  AI agents will use fallback logic (Ollama not available)")
        
        # Check MongoDB
        if not self.check_mongodb():
            print("❌ Failed to start MongoDB")
            return
        
        print("\n🎯 Starting services...")
        
        # Start backend
        backend = self.start_backend()
        time.sleep(3)
        
        # Start questionnaire
        questionnaire = self.start_questionnaire()
        time.sleep(3)
        
        # Display access information
        print("\n" + "=" * 60)
        print("✅ SYSTEM READY!")
        print("=" * 60)
        print("\n📊 ACCESS POINTS:")
        print("   🌐 Questionnaire UI: http://localhost:8001")
        print("   📚 Backend API Docs: http://localhost:8000/docs")
        print("   📖 Questionnaire API Docs: http://localhost:8001/docs")
        print("\n💡 FEATURES:")
        print("   • 8-question MVP questionnaire with AI helper")
        print("   • Intelligent existing policy analysis")
        print("   • Smart quote recommendations (only when beneficial)")
        print("   • Schema-enforced agent processing")
        print("   • 5 insurance companies with real quote engine")
        print("\n🎮 HOW TO USE:")
        print("   1. Open http://localhost:8001 in your browser")
        print("   2. Click 'Start Questionnaire'")
        print("   3. Answer questions (or use 'Need Help?' for AI assistance)")
        print("   4. Get intelligent analysis + quotes (only if needed)")
        print("\n⚡ Press Ctrl+C to stop all services")
        print("=" * 60)
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    demo = InsuranceDemo()
    demo.run()