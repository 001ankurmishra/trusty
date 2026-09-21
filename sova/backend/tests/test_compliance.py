import pytest
from app.agent.compliance import extract_and_evaluate

def test_compliance_engine():
    # Example sources
    sources = [
        {
            "chunk": "Maximum Allowable Working Pressure (MAWP): 150 PSI\nMaximum Operating Temperature: 85°C\nMinimum Wall Thickness: 12.5 mm",
            "filename": "SOP.pdf",
            "page": 1
        },
        {
            "chunk": "Operating Pressure: 165 PSI\nCurrent Temperature: 82°C\nMeasured Wall Thickness: 13.1 mm",
            "filename": "Inspection.pdf",
            "page": 2
        }
    ]
    
    table = extract_and_evaluate(sources, "Check compliance")
    
    # We expect 3 rules to match 3 measurements
    assert len(table) == 3
    
    # Find results by parameter (fuzzy match)
    results = {row["parameter"].lower(): row for row in table}
    
    # Operating pressure 165 PSI vs MAWP 150 = FAIL
    pressure = results["operating pressure"]
    assert pressure["status"] == "FAIL"
    
    # Temperature 82C vs max 85C = PASS
    temp = results["current temperature"]
    assert temp["status"] == "PASS"
    
    # Wall thickness 13.1 mm vs min 12.5 mm = PASS
    thick = results["measured wall thickness"]
    assert thick["status"] == "PASS"
