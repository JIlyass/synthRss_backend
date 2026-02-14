import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline

# ===============================
# FastAPI App
# ===============================

app = FastAPI(title="Article Summarizer API")

# ===============================
# CORS (autoriser Vercel + local)
# ===============================

origins = [
    "http://localhost:3000",  # dev local
    "https://synth-rss.vercel.app/",  # ⚠️ remplace par ton vrai domaine Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# Request Model
# ===============================

class Article(BaseModel):
    text: str

# ===============================
# Charger modèle BART
# ===============================

try:
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
except Exception as e:
    print(f"Erreur lors du chargement du modèle: {e}")
    summarizer = None

# ===============================
# Routes
# ===============================

@app.get("/")
def root():
    return {"message": "API is running"}

@app.post("/summarize")
async def summarize_article(article: Article):
    if not summarizer:
        raise HTTPException(status_code=500, detail="Modèle de résumé non disponible")

    if not article.text.strip():
        raise HTTPException(status_code=400, detail="Le texte est vide")

    try:
        summary = summarizer(
            article.text,
            max_length=150,
            min_length=30,
            do_sample=False
        )
        return {"summary": summary[0]["summary_text"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du résumé: {e}")

# ===============================
# Railway PORT Handling
# ===============================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
