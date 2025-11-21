from sentence_transformers import SentenceTransformer
import numpy as np, pandas as pd, geopandas as gpd

def build_text_embeddings(candidates: gpd.GeoDataFrame, poi_strings: list[str], model_name="sentence-transformers/all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name, device="cpu")
    embs = model.encode(poi_strings, normalize_embeddings=True)
    return np.array(embs)
