import pytest
import json
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

def test_agent_retry_loop(client, auth_headers):
    """End-to-end test validating the alias-based retry loop."""
    headers = auth_headers("admin", "admin123")
    
    # 1. Create project
    res = client.post("/projects", json={"name": "Retry Test", "description": "e2e retry"}, headers=headers)
    assert res.status_code == 200
    project_id = res.json()["id"]

    # Mock the LLM to return different responses for the generation vs the retry reformulation
    with patch("app.agent.llm_client.generate") as mock_gen, \
         patch("app.tools.rag_store.search") as mock_search, \
         patch("app.agent.verifier.verify_grounding") as mock_verify:
         
        # Make the first search return nothing (triggering retry) and the second return something
        mock_search.side_effect = [[], [{"chunk": "Wall temperature is 400C. Limit is 500C", "filename": "doc.pdf", "page": 1, "distance": 0.1, "doc_role": "SOP"}]]
        
        # Setup mock_gen to return a new query on the first call, and final text on the second
        def mock_generate(model, prompt, **kwargs):
            if "alternative search query" in prompt:
                return {"text": "wall temperature", "truncated": False}
            return {"text": "The wall temperature is 400C, which passes the limit of 500C.", "truncated": False}
        mock_gen.side_effect = mock_generate
        
        mock_verify.return_value = {"citations_valid": True, "numbers_grounded": True}

        task_res = client.post("/tasks", json={
            "project_id": project_id,
            "input_text": "Check the shell temperature."
        }, headers=headers)
        
        assert task_res.status_code == 200
        task_data = task_res.json()
        task_id = task_data["id"]
        
        # Poll for completion
        import time
        for _ in range(10):
            res = client.get(f"/tasks/{task_id}", headers=headers)
            if res.json()["status"] in ["COMPLETED", "AWAITING_APPROVAL", "FAILED"]:
                break
            time.sleep(0.5)
            
        task_data = client.get(f"/tasks/{task_id}", headers=headers).json()
        
        # The steps json should show the retry
        steps_str = json.dumps(task_data.get("steps", []))
        assert "Agent Reflects & Retries" in steps_str
        assert "wall temperature" in steps_str
