"""
rag_pipeline.py
Retrieval-Augmented Generation pipeline for medical documents:

  1. Load PDF / TXT / DOCX files
  2. Split them into overlapping chunks
  3. Embed the chunks (OpenAI or Google Gemini)
  4. Store embeddings in a persistent ChromaDB collection
  5. Retrieve the most relevant chunks for a query
"""

import os
from pathlib import Path

import chromadb
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path(os.getenv("DATA_DIR", "../data/medical_documents"))
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "medical_documents")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))


def get_provider() -> str:
    """Return the configured LLM/embedding provider ('openai' or 'gemini')."""
    return os.getenv("LLM_PROVIDER", "openai").lower()


def get_embeddings():
    """Return the embedding model selected via environment variables."""
    provider = get_provider()
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2", google_api_key=api_key
        )

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to the .env file.")
    return OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)


def get_collection():
    """Open (or create) the persistent Chroma collection."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(COLLECTION_NAME)


def load_document(file_path: str):
    """Load a .pdf, .txt or .docx file into LangChain documents."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(file_path)).load()
    if suffix == ".txt":
        return TextLoader(str(file_path), encoding="utf-8").load()
    if suffix == ".docx":
        return Docx2txtLoader(str(file_path)).load()
    raise ValueError(f"Unsupported file type: {suffix}")


def index_document(file_path: str) -> int:
    """
    Load, split, embed and store a document in ChromaDB.

    Returns the number of chunks stored. Upserting keeps the index
    idempotent if the same file is indexed more than once.
    """
    documents = load_document(file_path)
    if not documents:
        return 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    embeddings = get_embeddings()
    collection = get_collection()

    source = Path(file_path).name
    ids, texts, metadatas = [], [], []
    for i, chunk in enumerate(chunks):
        ids.append(f"{source}#{i}")
        texts.append(chunk.page_content)
        metadatas.append({"source": source})

    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings.embed_documents(texts),
    )
    return len(chunks)


def retrieve_context(query: str, k: int = RETRIEVAL_K) -> str:
    """Return the top-k most relevant document chunks for a query.

    Returns an empty string when there is no knowledge base yet or when
    retrieval fails, so the chatbot can fall back to general knowledge.
    """
    try:
        collection = get_collection()
        if collection.count() == 0:
            return ""

        embeddings = get_embeddings()
        result = collection.query(
            query_embeddings=embeddings.embed_query(query),
            n_results=min(k, collection.count()),
            include=["documents", "metadatas"],
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
    except Exception:
        return ""

    pieces = []
    for doc, meta in zip(documents, metadatas or []):
        source = (meta or {}).get("source", "unknown")
        pieces.append(f"[Source: {source}]\n{doc}")
    return "\n\n".join(pieces)
