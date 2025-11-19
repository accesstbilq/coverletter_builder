# apps/projects/rag_vectors.py
import math
from functools import lru_cache
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from .models import ProjectVector


@lru_cache(maxsize=1)
def get_project_retriever():
    """
    Build FAISS index from vectors stored in DB.
    Called once and cached, so retrieval is fast.
    """
    vectors = list(ProjectVector.objects.all())
    print(f"Loaded {len(vectors)} vectors from DB")
    # print(vectors)

    if not vectors:
        return FAISS.from_texts(["No projects found"], OpenAIEmbeddings()).as_retriever()

    # text_embeddings: list[(text, embedding)]
    text_embeddings: List[Tuple[str, List[float]]] = [
        (v.page_content, v.embedding) for v in vectors
    ]

    metadatas = [{"row_index": v.row_index} for v in vectors]

    embedding_fn = OpenAIEmbeddings()
    vectorstore = FAISS.from_embeddings(
        text_embeddings=text_embeddings,
        embedding=embedding_fn,
        metadatas=metadatas,
    )

    return vectorstore.as_retriever(search_kwargs={"k": 10})
