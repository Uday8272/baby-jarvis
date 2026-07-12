
## testing the rag engine before implementing it into the main workflow 

from rag_engine import load_and_chunk_docs, create_or_update_vector_store, ask_jarvis_local_files

# --- Note: Import your actual LLM here ---
# Example using a fake LLM or replace with your Jarvis LLM setup
from langchain_community.llms import FakeListLLM
fake_llm = FakeListLLM(responses=["This is a generated answer based on context."])

def main():
    # Create a dummy folder and put some text files inside to test
    target_folder = "./my_documents" 
    
    print("--- Phase 1: Ingestion ---")
    chunks = load_and_chunk_docs(target_folder)
    if chunks:
        create_or_update_vector_store(chunks)
    
    print("\n--- Phase 2: Asking a Question ---")
    question = "What does the documentation say about system tools?"
    
    # Swap `fake_llm` with your actual initialized LLM object from Jarvis
    answer, context_used = ask_jarvis_local_files(question, fake_llm)
    
    print("\n[Jarvis Answer]:")
    print(answer)
    
    print("\n[Sources Used]:")
    for doc in context_used:
        print(f"- {doc.metadata.get('source', 'Unknown')} (Snippet: {doc.page_content[:50]}...)")

if __name__ == "__main__":
    main()
