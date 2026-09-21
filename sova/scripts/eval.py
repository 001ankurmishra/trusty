#!/usr/bin/env python3
"""
FR-20 Small Evaluation Script
Runs a set of prompts through the orchestrator and verifies the output
against expected values (numerical extraction or specific keywords).
"""
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(BACKEND_DIR)

from app.agent.orchestrator import run_task
from app.core.db import SessionLocal, Project
from docx import Document

# Test suite
TESTS = [
    {
        "name": "Math calculation (safe)",
        "prompt": "Calculate (245 * 3.7) + 12",
        "expected_substrings": ["918.5"],
        "needs_project": False
    },
    {
        "name": "Python Sandbox Execution",
        "prompt": "Write a Python script to calculate the 10th Fibonacci number.",
        "expected_substrings": ["55"],
        "needs_project": False
    },
    {
        "name": "SOP Grounded Extraction",
        "prompt": "According to the SOP, what is the Maximum Allowable Working Pressure?",
        "expected_substrings": ["150", "PSI"],
        "needs_project": True
    },
    {
        "name": "Compliance Failure Detection",
        "prompt": "Analyze the inspection report for V-102 against our SOP limits.",
        "expected_substrings": ["FAIL", "165"],
        "needs_project": True
    },
    {
        "name": "Unrelated prompt rejection",
        "prompt": "Write a poem about a pressure vessel.",
        "expected_substrings": ["poem", "vessel"],
        "needs_project": False
    }
]

def main():
    print("Starting TrustForge Eval...")
    db = SessionLocal()
    proj = db.query(Project).filter(Project.name == "Sector 7 Safety Review").first()
    
    project_id = proj.id if proj else "no-project"
    
    if not proj:
        print("Warning: Seed project 'Sector 7 Safety Review' not found. Some tests will fail.")
        print("Run `python sova/scripts/seed_demo.py` first.")

    passed = 0
    total = len(TESTS)

    for i, t in enumerate(TESTS):
        print(f"\n--- Test {i+1}/{total}: {t['name']} ---")
        prompt = t["prompt"]
        print(f"Prompt: {prompt}")
        
        # Run orchestrator
        # We don't need a real user role here for most tests, but we'll use "ADMIN"
        res = run_task(prompt, project_id if t["needs_project"] else "", user_role="ADMIN")
        
        result_text = res.get("result_text", "")
        # Also check the compliance table if present
        table_text = str(res.get("compliance_table", []))
        combined_text = result_text + " " + table_text
        
        # Check substrings
        failed_subs = [s for s in t["expected_substrings"] if s.lower() not in combined_text.lower()]
        
        if not failed_subs:
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL. Missing substrings: {failed_subs}")
            print(f"Output received:\n{combined_text[:300]}...")

        # Also print routing information
        route = res.get("route_info", {})
        print(f"Routed to: {route.get('selected_model')}")

    print("\n===============================")
    print(f"Eval Complete. Score: {passed}/{total} ({(passed/total)*100:.1f}%)")
    print("===============================")
    
if __name__ == "__main__":
    main()
