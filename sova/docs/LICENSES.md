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

> [!WARNING]
> **Non-Commercial Model Limitation**
> 
> By default, TrustForge uses **Qwen2.5-3B** (and Qwen2.5-Coder:1.5b) as the default models to run efficiently on 16GB RAM laptops. 
> 
> **Qwen Research License is Non-Commercial.** If you are deploying TrustForge in a commercial environment or running a commercial pilot, you **must swap this out for a permissively licensed model** (e.g., Llama 3 8B (Llama 3 License) or Mistral 0.3 (Apache 2.0)). You can swap models via the `.env` configuration file without changing any code.

| Model | Default Use | License | Commercial Use? |
| :--- | :--- | :--- | :--- |
| **Qwen2.5-3B-Instruct** | Reasoning / Extraction | Tongyi Qianwen License Agreement / Research | **No** (Requires explicit permission for >100M MAU, but effectively Non-Commercial for general research) |
| **Qwen2.5-Coder:1.5B** | Code / Logic | Tongyi Qianwen License Agreement / Research | **No** |
| **Moondream2** | Vision | Apache 2.0 | **Yes** |
| **all-MiniLM-L6-v2** | Embeddings | Apache 2.0 | **Yes** |

## How to Swap Models

To swap out Qwen for a commercial-friendly model, edit your `.env` file:
```env
REASONING_MODEL="llama3"
CODING_MODEL="llama3"
```
Ensure that you have pulled the model to your Ollama server before starting tasks (`ollama pull llama3`).
