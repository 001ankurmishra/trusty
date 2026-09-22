import re
with open("app/agent/orchestrator.py", "r") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "# 3. RETRIEVE (Enterprise RAG)" in line:
        start_idx = i
    elif "# 7. HUMAN REVIEW GATE" in line:
        end_idx = i
        break

pre_loop = lines[:start_idx]
post_loop = lines[end_idx:]
loop_content = lines[start_idx:end_idx]

new_loop = [
    "        search_query = task_text\n",
    "        max_attempts = 2\n",
    "        for attempt in range(max_attempts):\n",
    "            compliance_table = []\n"
]

for line in loop_content:
    if "rag_store.search(task_text" in line:
        line = line.replace("task_text", "search_query")
    if "compliance_table = _extract_compliance_table(sources, task_text," in line:
        line = line.replace("task_text", "search_query")
    
    # Indent by 4 spaces because it is now inside a for loop
    if line.strip():
        new_loop.append("    " + line)
    else:
        new_loop.append(line)

retry_logic = """
            needs_retry = False
            retry_reason = ""
            
            if not verification.get("citations_valid", True) or not verification.get("numbers_grounded", True):
                needs_retry = True
                retry_reason = "Verifier flagged ungrounded citations/numbers."
            
            if compliance_table:
                for row in compliance_table:
                    if row.get("status") == "NEEDS_REVIEW" and row.get("limit") == "No matching rule":
                        needs_retry = True
                        retry_reason = f"No matching rule found for parameter: {row.get('parameter')}"
                        break
                        
            if needs_retry and attempt < max_attempts - 1:
                prompt = f"The query '{search_query}' failed because: {retry_reason}\\nProvide a single alternative search query (e.g. synonyms, different phrasing) to find the missing information. Output ONLY the new query."
                try:
                    new_query, _, _, _ = _generate_with_fallback(route_info, prompt, max_tokens=50)
                    search_query = new_query.strip().strip('"').strip("'")
                    _step(steps, "Agent Reflects & Retries", "WAITING", f"Retrying with alias/new query: '{search_query}'. Reason: {retry_reason}", step_callback)
                    continue
                except LLMError as e:
                    pass
            break
"""

new_loop.extend([line + "\n" for line in retry_logic.split("\n")[1:]])

with open("app/agent/orchestrator.py", "w") as f:
    f.writelines(pre_loop + new_loop + post_loop)
