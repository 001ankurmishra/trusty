import os
import sys
import time
import importlib
import traceback
import argparse

# Ensure backend path is configured
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

def run_golden_tests():
    from tests.golden.test_compliance_golden import test_golden_compliance
    
    tests = [
        test_golden_compliance
    ]
    
    passed = 0
    failed = 0
    
    for t in tests:
        try:
            t()
            passed += 1
        except Exception:
            failed += 1
            
    return passed, failed

def main():
    parser = argparse.ArgumentParser(description="Benchmark LLMs against TrustForge golden tests")
    parser.add_argument("--models", type=str, default="qwen2.5:3b-instruct", help="Comma-separated list of models to test")
    args = parser.parse_args()
    
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    
    print(f"Benchmarking {len(models)} models against Golden Tests...")
    print("\n| Model | Passed | Failed | Total Time (s) | Avg Latency (s/test) | Status |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for model in models:
        os.environ["REASONING_MODEL"] = model
        # Force config reload if it was already loaded
        if "app.core.config" in sys.modules:
            importlib.reload(sys.modules["app.core.config"])
        
        start_time = time.time()
        
        try:
            passed, failed = run_golden_tests()
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / (passed + failed) if (passed + failed) > 0 else 0
            
            status = "✅ PASS" if failed == 0 else "❌ FAIL"
            
            print(f"| {model} | {passed} | {failed} | {total_time:.2f}s | {avg_time:.2f}s | {status} |")
        except Exception as e:
            print(f"| {model} | 0 | 0 | ERROR | ERROR | ⚠️ {str(e)[:40]} |")

if __name__ == "__main__":
    main()
