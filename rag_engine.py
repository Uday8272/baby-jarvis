# this handles the reading of the local files in the system and splittign them into chunks

import os 
from langchain_community.document_loaders import DirectoryLoader, TextLoader 
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter 

def load_and_chunk_docs(director_path: str): 
    print(f'scanning directory: {director_path}....') 

    # we use a mapping to handle different file types 
    loaders={
        '.txt': TextLoader, 
        '.pdf': PyPDFLoader, 
        '.docx': Docx2txtLoader
    } 

    documents = [] 

    # iterate through all files in the directory 
    for root, _, files in os.walk(director_path):
        for file in files: 
            file_extension = os.path.splitext(file)[1].lower()
            file_path = os.path.join(root, file)

            if file_extension in loaders:
                try:
                    # load the document using the appropriate loader 
                    loader_class = loaders[file_extension] 
                    loader = loader_class(file_path)
                    documents.extend(loader.load())
                    print(f'loaded: {file}')
                except Exception as e:
                    print(f'error loading {file}: {e}') 

    # chunk the documents into smaller pieces 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, # number of characters per chunk
        chunk_overlap=200 # overlap to maintain context between chunks
    ) 

    chunks = text_splitter.split_documents(documents) 
    print(f'split into {len(chunks)} chunks.')

    return chunks 


# now these chunks have to be converted into vectors and to be stored locally 
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_community.vectorstores import Chroma 

# path to save the local database 
CHROMA_PATH = './chroma_db'
 
def create_or_update_vector_store(chunks):
    print('initializing embedding model...')
    embeddings=HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')

    print('building local vector database...')
    # thsi creates a local sqlite dataabse in the chroma_path folder 
    vector_store=Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    ) 

    print('vector db created/updated successfully')
    return vector_store 

def get_vector_store():
    # helper to load the db later without recreating it 
    embeddings=HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
    return Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings) 


## now we connect the vector db to an llm depending on what llm jarvis uses 

from langchain_classic.chains import create_retrieval_chain 
from langchain_classic.chains.combine_documents import create_stuff_documents_chain 
from langchain_core.prompts import ChatPromptTemplate 

def ask_jarvis_local_files(query: str, llm):
    ## load the existing vector database 
    vector_store = get_vector_store() 

    ## set up the retriever 
    retriever = vector_store.as_retriever(search_kwargs={'k': 4})

    # define how jarvis should answer  based on te retrieved context 
    system_prompt = (
        "You are Jarvis, an AI assistant. Use the following pieces of retrieved "
        "context to answer the question. If the answer is not in the context, "
        "say that you don't know. Do not make up information.\n\n"
        "Context:\n{context}"
    ) 

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]) 


    #chain everything together 
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    # 5. Get the response
    print("Jarvis is thinking...")
    response = rag_chain.invoke({"input": query})
    
    return response["answer"], response["context"]
