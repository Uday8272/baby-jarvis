"""
rag_tool.py — LangChain tools that let Jarvis search local documents.

Two tools are exposed:
    1. search_local_files  — query the vector DB for relevant document chunks
    2. ingest_local_folder — scan a folder and build/refresh the vector DB

These are registered in ALL_TOOLS so the ReAct agent can call them autonomously.
"""

from langchain_core.tools import tool

# ── Tool 1: Query the local knowledge base ──────────────────────────────────

@tool
def search_local_files(query: str) -> str:
    """Search through locally indexed documents (PDFs, TXT, DOCX) to find
    information relevant to the user's question. Use this tool when the user
    asks about the contents of their local files, personal documents, notes,
    or any data stored on their PC that has been previously ingested.

    Args:
        query: The natural-language question to search for in local documents.

    Returns:
        A formatted string with the top matching document snippets and their
        source file paths, or a message saying no results were found.
    """
    try:
        from rag_engine import get_vector_store

        vector_store = get_vector_store()

        # retrieve the top 4 most relevant chunks
        results = vector_store.similarity_search(query, k=4)

        if not results:
            return "No relevant documents found in the local knowledge base. The user may need to ingest files first."

        # format the results nicely for the LLM
        formatted = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "Unknown file")
            snippet = doc.page_content[:500]
            formatted.append(f"--- Result {i} ---\nSource: {source}\nContent:\n{snippet}\n")

        return "\n".join(formatted)

    except Exception as e:
        return f"Error searching local files: {e}. Make sure files have been ingested first using the ingest_local_folder tool."


# ── Tool 2: Ingest / refresh the knowledge base ─────────────────────────────

@tool
def ingest_local_folder(folder_path: str) -> str:
    """Scan a folder on the user's PC, read all supported documents (PDF, TXT,
    DOCX), split them into chunks, and store them in the local vector database
    so they can be searched later with search_local_files.

    Use this when the user says things like:
    - "Index my documents folder"
    - "Learn from my notes in D:/Notes"
    - "Refresh the knowledge base"

    Args:
        folder_path: The absolute path to the folder to scan (e.g. "D:/Documents").

    Returns:
        A status message confirming how many files and chunks were processed.
    """
    import os

    if not os.path.isdir(folder_path):
        return f"Error: '{folder_path}' is not a valid directory."

    try:
        from rag_engine import load_and_chunk_docs, create_or_update_vector_store

        chunks = load_and_chunk_docs(folder_path)

        if not chunks:
            return f"No supported documents (.txt, .pdf, .docx) found in '{folder_path}'."

        create_or_update_vector_store(chunks)

        return f"Successfully ingested {len(chunks)} chunks from '{folder_path}' into the local knowledge base."

    except Exception as e:
        return f"Error during ingestion: {e}"
