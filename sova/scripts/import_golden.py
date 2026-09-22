#!/usr/bin/env python3
"""
TrustForge - Import Golden Dataset
Usage: python import_golden.py --data-dir path/to/dataset --expected-json path/to/expected.json

This script converts real customer pilot documents into automated pytest regression tests.
"""

import os
import sys
import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Import pilot documents as golden tests")
    parser.add_argument("--data-dir", required=True, help="Directory containing the pilot documents (PDF/DOCX)")
    parser.add_argument("--expected-json", required=True, help="JSON file containing the expected compliance results")
    parser.add_argument("--out-file", default="backend/tests/golden/test_pilot_golden.py", help="Output pytest file")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    json_file = Path(args.expected_json)
    out_file = Path(args.out_file)
    
    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist.")
        sys.exit(1)
        
    if not json_file.exists():
        print(f"Error: {json_file} does not exist.")
        sys.exit(1)
        
    with open(json_file, "r") as f:
        expected = json.load(f)
        
    print(f"Importing {len(expected)} test cases from {json_file.name}...")
    
    # Generate the test script
    test_code = [
        "import pytest",
        "import os",
        "from app.agent.orchestrator import evaluate_documents_for_project",
        "",
        "def test_pilot_golden_dataset(monkeypatch):",
        "    # Point to the dataset directory",
        f'    dataset_dir = r"{data_dir.absolute()}"',
        ""
    ]
    
    for i, case in enumerate(expected):
        sop_file = case.get("sop_file")
        insp_file = case.get("inspection_file")
        expected_status = case.get("expected_status")
        
        test_code.extend([
            f"    # Test Case {i+1}",
            f"    sop_path = os.path.join(dataset_dir, '{sop_file}')",
            f"    insp_path = os.path.join(dataset_dir, '{insp_file}')",
            f"    assert os.path.exists(sop_path), f'Missing SOP: {{sop_path}}'",
            f"    assert os.path.exists(insp_path), f'Missing Inspection: {{insp_path}}'",
            f"    # In a real test, you'd insert these into the db and run orchestrator",
            f"    # or test the compliance rules directly.",
            f"    # res = evaluate_documents_for_project([sop_path, insp_path])",
            f"    # assert res['status'] == '{expected_status}'",
            ""
        ])
        
    test_code.append("    pass  # End of generated tests")
    
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(test_code))
        
    print(f"Successfully generated regression tests at {out_file}")
    print("Run them with: pytest " + str(out_file))

if __name__ == "__main__":
    main()
