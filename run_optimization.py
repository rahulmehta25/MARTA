#!/usr/bin/env python3
"""
MARTA Route Optimization Runner
Executes the complete optimization workflow
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Main runner function"""
    print("🚇 MARTA Route Optimization & Simulation Engine")
    print("=" * 60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('src/optimization/optimization_orchestrator.py'):
        print("❌ Error: Please run this script from the MARTA project root directory")
        sys.exit(1)
    
    # Import and run the orchestrator
    try:
        from src.optimization.optimization_orchestrator import main as run_orchestrator
        success = run_orchestrator()
        
        if success:
            print("\n🎉 Optimization workflow completed successfully!")
            print("📊 Check the generated reports and files for results")
        else:
            print("\n⚠️ Optimization workflow completed with issues")
            print("📋 Check the logs for details")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 