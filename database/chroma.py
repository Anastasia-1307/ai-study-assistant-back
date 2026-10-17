import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_or_create_collection(
    name="study_documents",
    embedding_function=embedding_function,
)