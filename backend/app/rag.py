import os
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings

class RAGEngine:
    def __init__(self):
        # Allow user to set key via env, or rely on them setting it globally
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
             print("WARNING: GOOGLE_API_KEY not found in env.")

        # Use Google Gemini Embeddings (API-based, huge RAM savings)
        print("Initializing Google Gemini Embeddings...")
        if not api_key:
             raise ValueError("GOOGLE_API_KEY is required for Gemini Embeddings.")
             
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
        
        self.vector_store = Chroma(
            collection_name="tourism_tunisia",
            embedding_function=self.embeddings,
            persist_directory="./chroma_db"
        )
        
        # Configure Google GenAI directly (for chat)
        if api_key:
            genai.configure(api_key=api_key)
            self.llm = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.llm = None
        
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    def ingest(self, text: str, source: str):
        if not text:
            return
        
        docs = [Document(page_content=text, metadata={"source": source})]
        splits = self.text_splitter.split_documents(docs)
        if splits and self.embeddings:
            self.vector_store.add_documents(splits)

    def query(self, question: str):
        if not self.llm:
            return {"answer": "Error: LLM not initialized (missing GOOGLE_API_KEY).", "sources": []}
            
        # Retrieve relevant documents
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.get_relevant_documents(question)
        
        # Build context from retrieved documents
        context = "\n\n".join([f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}" for doc in relevant_docs])
        sources = [doc.metadata.get("source", "Unknown") for doc in relevant_docs]
        
        # Create prompt
        prompt = f"""You are a smart and helpful tourism assistant for Tunisia. Use the following context to answer the user's question in detail.
        
Guidelines:
1. Use the provided Context to answer the question faithfully.
2. If the context contains reviews or opinions, summarize them to give an honest perspective.
3. If the context doesn't fully answer the question, you may supplement with your general knowledge but clearly state what is from the context and what is general knowledge.
4. Cite your sources implicitly in the text (e.g., "According to...") or explicitly if relevant.
5. Search results might contain repetitive content; synthesize it into a coherent answer.
6. When you mention a specific location, restaurant, or hotel, provide a Google Maps search link for it. Format: [Location Name](https://www.google.com/maps/search/?api=1&query=Location+Name).
{context}

Question: {question}

Answer:"""
        
        # Generate response using Google GenAI
        try:
            response = self.llm.generate_content(prompt)
            answer = response.text
        except Exception as e:
            answer = f"Error generating response: {str(e)}"
        
        return {
            "answer": answer,
            "sources": sources
        }
