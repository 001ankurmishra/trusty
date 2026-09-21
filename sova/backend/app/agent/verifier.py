import re

def verify_grounding(result_text: str, sources: list) -> dict:
    """
    Verifies that the generated text is grounded in the provided sources.
    1. Checks if all [filename p.N] citations in the text actually exist in sources.
    2. Extracts numbers with units from the text and checks if they appear in the sources.
    """
    verification = {
        "citations_valid": True,
        "unsupported_citations": [],
        "numbers_grounded": True,
        "unsupported_numbers": [],
    }
    
    if not sources:
        # If there's no sources, we can't really ground citations or numbers to sources.
        return verification

    # Combine all source text for easy searching
    all_source_text = " ".join([s.get("chunk", "") for s in sources]).lower()

    # 1. Validate citations e.g. [filename.pdf p.1]
    citation_pattern = re.compile(r"\[(.*?)\s+p\.(\d+)\]", re.IGNORECASE)
    citations = citation_pattern.findall(result_text)
    
    for filename, page in citations:
        filename = filename.strip()
        page = page.strip()
        # Check if there is a source matching this filename and page
        matched = False
        for s in sources:
            if s.get("filename", "").lower() == filename.lower() and str(s.get("page")) == page:
                matched = True
                break
        if not matched:
            verification["citations_valid"] = False
            verification["unsupported_citations"].append(f"[{filename} p.{page}]")

    # 2. Extract numbers + units from the result_text and see if they exist in source text
    # e.g., 100 PSI, 50.5%, 2.5 mm
    number_pattern = re.compile(r"\b(\d+(?:\.\d+)?)\s*([a-zA-Z°%/-]+)\b")
    numbers_found = number_pattern.findall(result_text)
    
    for val, unit in numbers_found:
        # Skip common non-measurement words that might get caught as units
        if unit.lower() in {"and", "the", "to", "of", "in", "is", "for", "a", "an", "on", "page", "p", "step"}:
            continue
            
        search_str = f"{val}{unit}".lower()
        search_str_spaced = f"{val} {unit}".lower()
        
        if search_str not in all_source_text and search_str_spaced not in all_source_text:
            verification["numbers_grounded"] = False
            verification["unsupported_numbers"].append(f"{val} {unit}")

    return verification
