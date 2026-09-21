import pytest
from unittest.mock import patch

def test_smoke_e2e(client, auth_headers):
    """End-to-end smoke test through the whole system."""
    
    # 1. Login as admin
    headers = auth_headers("admin", "admin123")
    
    # 2. Create project
    res = client.post("/projects", json={"name": "Smoke Test", "description": "e2e"}, headers=headers)
    assert res.status_code == 200
    project_id = res.json()["id"]
    
    # 3. Upload document (skip for now to avoid dealing with file multipart in this simple smoke test)
    # 4. Run task with mocked LLM
    with patch("app.agent.llm_client.generate") as mock_gen:
        mock_gen.return_value = {"text": "This is a mocked LLM response saying PASS.", "truncated": False}
        
        task_res = client.post("/tasks", json={
            "project_id": project_id,
            "input_text": "Is this safe to approve?"
        }, headers=headers)
        
        assert task_res.status_code == 200
        task_id = task_res.json()["id"]
        assert task_res.json()["status"] in ["RECEIVED", "RUNNING", "DONE", "WAITING"]
    
    # 5. Check audit log
    audit_res = client.get(f"/audit/project/{project_id}", headers=headers)
    assert audit_res.status_code == 200
    assert len(audit_res.json()) > 0
