"""
Singleton Sentence Transformers model.
Model di-load sekali saat pertama dipakai, lalu di-cache di memory.
"""
from sentence_transformers import SentenceTransformer
from app.config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[Embedding] Loading model '{settings.embedding_model}'...")
        _model = SentenceTransformer(settings.embedding_model)
        print("[Embedding] Model ready.")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Ubah list teks menjadi list vector embedding."""
    model = get_model()
    vectors = model.encode(texts, convert_to_numpy=True)
    return vectors.tolist()
