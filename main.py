
import os
import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()

import ollama
from fastapi import FastAPI


from uuid import uuid4
from io import BytesIO
from pypdf import PdfReader


from fastapi import UploadFile, File, HTTPException
from models.schemas import StudyRequest
from fastapi.middleware.cors import CORSMiddleware
from database.chroma import collection
from services.ai_service import split_text, generate_material


app = FastAPI(title="AI Study Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def home():
    return {"message": "AI Study Assistant functioneaza!"}



@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Încarcă un fișier PDF."
        )

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Fișierul nu poate depăși 10 MB."
        )

    try:
        reader = PdfReader(BytesIO(content))

        if reader.is_encrypted:
            raise HTTPException(
                status_code=400,
                detail="PDF-ul este protejat prin parolă."
            )

        # Extragem textul din fiecare pagină.
        pages_text = [
            page.extract_text() or ""
            for page in reader.pages
        ]

        text = "\n".join(pages_text).strip()

        if not text:
            raise HTTPException(
                status_code=400,
                detail="Nu am putut extrage textul din PDF."
            )

        # Generăm ID-ul înainte de a crea metadatele.
        document_id = str(uuid4())

        # Împărțim textul în fragmente și păstrăm metadatele.
        chunks = []
        metadatas = []

        for page_number, page_text in enumerate(
            pages_text, start=1
        ):
            for chunk in split_text(page_text):
                chunks.append(chunk)
                metadatas.append({
            "document_id": document_id,
            "filename": file.filename or "document.pdf",
            "page": page_number
        })

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="PDF-ul nu conține fragmente de text valide."
            )


        ids = [
            f"{document_id}_{i}"
            for i in range(len(chunks))
        ]

        # ChromaDB generează embeddings și salvează datele.
        collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )

        return {
            "message": "PDF-ul a fost procesat și salvat în ChromaDB.",
            "document_id": document_id,
            "filename": file.filename,
            "pages": len(reader.pages),
            "characters": len(text),
            "chunks_saved": len(chunks)
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="PDF-ul nu a putut fi procesat sau salvat."
        )
    finally:
        await file.close()


@app.post("/search-document")
async def search_document(question: str):
    if not question.strip():
        raise HTTPException(
            status_code=400,
            detail="Introdu o întrebare."
        )

    results = collection.query(
        query_texts=[question],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]

    if not documents:
        return {
            "question": question,
            "results": []
        }

    return {
        "question": question,
        "results": [
            {
                "text": document,
                "filename": metadata["filename"],
                "page": metadata["page"],
                "distance": distance
            }
            for document, metadata, distance in zip(
                documents,
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    }


@app.post("/generate-material")
async def generate_study_material(request: StudyRequest):
    return generate_material(request)

@app.get("/documents")
async def get_documents():
    results = collection.get(
        include=["metadatas"]
    )

    metadatas = results.get("metadatas") or []
    ids = results.get("ids") or []

    documents = {}

    for metadata in metadatas:
        if not metadata:
            continue

        document_id = metadata.get("document_id")

        if document_id:
            documents[document_id] = {
                "document_id": document_id,
                "filename": metadata.get("filename"),
            }

    return {
        "total_chunks": len(ids),
        "total_documents": len(documents),
        "documents": list(documents.values()),
    }