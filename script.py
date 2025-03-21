import os
import fitz  # PyMuPDF for PDFs
import docx
import faiss
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

# LLM Foundry API Configuration
LLMFOUNDRY_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6Im5paGFsLmJhZGlnZXJAZ3JhbWVuZXIuY29tIn0.T9jSe5tAEqFIGdc74IffgTEvHfAG4Ve0c0hWb1zo-Io"
LLMFOUNDRY_PROJECT = "my-test-project"
LLMFOUNDRY_BASE_URL = "https://llmfoundry.straive.com/openai/v1/chat/completions"

FOLDER_PATH = "test_embed"  # Change this to your document folder

# Load a better model for embeddings
model = SentenceTransformer("all-mpnet-base-v2")

# Function to extract text from PDFs
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text("text") for page in doc])
    return text.lower()  # Lowercasing for consistency

# Function to extract text from Word docs
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.lower()

# Load and process all PDFs and DOCX files in the subfolder
documents = []
file_paths = []

for file in os.listdir(FOLDER_PATH):
    full_path = os.path.join(FOLDER_PATH, file)
    
    if file.endswith(".pdf"):
        text = extract_text_from_pdf(full_path)
        documents.append((text, full_path))  # Store text + file name
    elif file.endswith(".docx"):
        text = extract_text_from_docx(full_path)
        documents.append((text, full_path))

# Generate embeddings with normalization
doc_texts = [doc[0] for doc in documents]  # Extract text only
doc_embeddings = model.encode(doc_texts, normalize_embeddings=True, convert_to_numpy=True)

# Convert embeddings to float (required for FAISS)
doc_embeddings = np.array(doc_embeddings, dtype=np.float64)

# Use FAISS HNSW indexing for better recall
dimension = doc_embeddings.shape[1]
index = faiss.IndexHNSWFlat(dimension, 32)  # Graph-based indexing
index.hnsw.efConstruction = 64
index.add(doc_embeddings)

# Function to retrieve relevant documents & extract relevant text
def search_documents(query, top_k=3):
    query_embedding = model.encode([query.lower()], normalize_embeddings=True, convert_to_numpy=True)
    query_embedding = np.array(query_embedding, dtype=np.float64)

    distances, indices = index.search(query_embedding, top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if 0 <= idx < len(documents):
            doc_text, file_path = documents[idx]
            
            # Extract relevant passage
            extracted_snippet = extract_relevant_passage(doc_text, query)
            
            results.append({
                "file": file_path,
                "score": distances[0][i],
                "snippet": extracted_snippet
            })
    
    return results

# Function to extract the most relevant text snippet
def extract_relevant_passage(text, query, window=300):
    sentences = text.split(". ")  # Simple sentence split
    query_words = set(query.lower().split())  # Convert query to set of words
    
    best_snippet = ""
    best_score = 0

    for sentence in sentences:
        words = set(sentence.lower().split())
        common_words = query_words.intersection(words)
        score = len(common_words)
        
        if score > best_score:
            best_score = score
            best_snippet = sentence
    
    return best_snippet[:window]  # Limit snippet size

# Function to generate a refined answer using LLM Foundry
def generate_llm_response(query, context):
    headers = {"Authorization": f"Bearer {LLMFOUNDRY_TOKEN}:{LLMFOUNDRY_PROJECT}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}\n\nProvide a detailed response."}
        ]
    }

    response = requests.post(LLMFOUNDRY_BASE_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.json()}"

# Interactive search
while True:
    user_query = input("\nEnter your search query (or type 'exit' to quit): ")
    if user_query.lower() == "exit":
        break
    
    search_results = search_documents(user_query)
    
    print("\n🔍 Top relevant documents & extracted text:")
    context_text = ""
    
    for result in search_results:
        print(f"\n📄 {result['file']} (Score: {result['score']:.4f})")
        print(f"📝 Extracted Snippet: {result['snippet'][:300]}...")  # Show snippet
        context_text += result['snippet'] + "\n\n"
    
    # Generate an LLM-based refined response
    llm_answer = generate_llm_response(user_query, context_text)
    
    print("\n🤖 **LLM Response:**")
    print(llm_answer)
