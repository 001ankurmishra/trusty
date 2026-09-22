# TrustForge Software Licenses

TrustForge is built on a stack of open-source software and open-weights models. When deploying for a commercial pilot, you must ensure compliance with all underlying licenses.

## Software Stack (Permissive / Open Source)

| Component | License | Notes |
| :--- | :--- | :--- |
| **FastAPI** | MIT | Core backend framework. |
| **React** | MIT | Core frontend UI framework. |
| **Vite** | MIT | Frontend bundler. |
| **TailwindCSS** | MIT | CSS utility framework. |
| **SQLite** | Public Domain | Database engine. |
| **ChromaDB** | Apache 2.0 | Vector database for RAG. |
| **SentenceTransformers** | Apache 2.0 | Embedding model wrapper. |
| **PyMuPDF** | GNU Affero GPL v3 (AGPL) | **WARNING:** If you modify TrustForge and expose it as a network service, you must disclose source code. Alternatively, consider dual-licensing or replacing it if AGPL is not permitted by your legal team. |
| **Ollama** | MIT | Local inference engine. |

## AI Models

| Model | Default Use | License | Commercial Use? |
| :--- | :--- | :--- | :--- |
| **Llama3.2** | Reasoning / Extraction | Llama 3.2 Community License | **Yes** (Commercial use permitted subject to terms) |
| **Qwen2.5-Coder:1.5B** | Code / Logic | Apache 2.0 | **Yes** |
| **Moondream2** | Vision | Apache 2.0 | **Yes** |
| **all-MiniLM-L6-v2** | Embeddings | Apache 2.0 | **Yes** |

## Optional: How to Swap Models

If you wish to use different models, you can edit your `.env` file:
```env
REASONING_MODEL="qwen2.5:3b-instruct"
CODING_MODEL="qwen2.5-coder:1.5b"
```
Ensure that you have pulled the model to your Ollama server before starting tasks (`ollama pull qwen2.5:3b-instruct`).
