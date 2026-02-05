import pandas as pd
import os
import pickle
import faiss
from sentence_transformers import SentenceTransformer

CSV_PATH = "WA_Fn-UseC_-HR-Employee-Attrition.csv"
INDEX_PATH = "faiss.index"
DOCS_PATH = "docs.pkl"

def row_to_text(row: pd.Series) -> str:
    # Turn each employee row into a readable “fact block”
    parts = []
    for col, val in row.items():
        parts.append(f"{col}: {val}")
    return " | ".join(parts)

def main():
    df = pd.read_csv(CSV_PATH)

    # Convert rows -> text docs
    docs = [row_to_text(df.iloc[i]) for i in range(len(df))]

    # Embedding model (local)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Create embeddings
    embeddings = model.encode(docs, show_progress_bar=True)
    embeddings = embeddings.astype("float32")

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save index + docs
    faiss.write_index(index, INDEX_PATH)
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(docs, f)

    print("✅ Built RAG index successfully!")
    print("Docs:", len(docs))
    print("Saved:", INDEX_PATH, DOCS_PATH)

if __name__ == "__main__":
    main()
