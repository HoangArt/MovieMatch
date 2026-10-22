from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "data" / "ml-latest-small"
MOVIES_FILE = DATASET_DIR / "movies.csv"
TAGS_FILE = DATASET_DIR / "tags.csv"


@st.cache_resource(show_spinner="Đang chuẩn bị mô hình gợi ý theo nội dung...")
def load_content_index():
    """
    Xây dựng ma trận TF-IDF cho từng phim từ title, genres và tags.

    Hàm được cache trong bộ nhớ để không phải huấn luyện vectorizer
    lại sau mỗi lần Streamlit rerun.
    """
    if not MOVIES_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy dữ liệu phim: {MOVIES_FILE}")

    movies = pd.read_csv(MOVIES_FILE)
    movies["movieId"] = pd.to_numeric(movies["movieId"], errors="coerce")
    movies = movies.dropna(subset=["movieId"]).copy()
    movies["movieId"] = movies["movieId"].astype(int)
    movies["title"] = movies["title"].fillna("").astype(str)
    movies["genres"] = movies["genres"].fillna("").astype(str)

    # Gom tags thành một chuỗi mô tả cho từng movieId.
    if TAGS_FILE.exists():
        tags = pd.read_csv(TAGS_FILE)
        if {"movieId", "tag"}.issubset(tags.columns):
            tags["movieId"] = pd.to_numeric(tags["movieId"], errors="coerce")
            tags = tags.dropna(subset=["movieId", "tag"])
            tags["movieId"] = tags["movieId"].astype(int)
            tags["tag"] = tags["tag"].fillna("").astype(str)
            tag_text = tags.groupby("movieId")["tag"].agg(" ".join)
            movies["tags_text"] = movies["movieId"].map(tag_text).fillna("")
        else:
            movies["tags_text"] = ""
    else:
        movies["tags_text"] = ""

    # Tên phim, thể loại và tags cùng tạo nên vector đặc trưng nội dung.
    title_text = movies["title"].str.replace(r"\s*\(\d{4}\)\s*$", "", regex=True)
    genre_text = movies["genres"].str.replace("|", " ", regex=False)
    documents = title_text + " " + genre_text + " " + movies["tags_text"]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=50000,
    )
    tfidf_matrix = vectorizer.fit_transform(documents)
    movie_to_idx = {
        int(movie_id): idx
        for idx, movie_id in enumerate(movies["movieId"].tolist())
    }

    return movies, tfidf_matrix, movie_to_idx


def recommend_by_favorite_movies(favorite_movie_ids, top_k=12):
    """Xếp hạng phim chưa chọn theo cosine similarity hồ sơ TF-IDF."""
    movies, tfidf_matrix, movie_to_idx = load_content_index()

    valid_ids = [
        int(movie_id)
        for movie_id in favorite_movie_ids
        if int(movie_id) in movie_to_idx
    ]
    if not valid_ids:
        return pd.DataFrame(columns=["movieId", "title", "genres", "similarity"])

    favorite_indices = [movie_to_idx[movie_id] for movie_id in valid_ids]
    # Trung bình vector các phim yêu thích tạo thành hồ sơ sở thích người dùng.
    user_profile = np.asarray(tfidf_matrix[favorite_indices].mean(axis=0))
    similarities = cosine_similarity(user_profile, tfidf_matrix).ravel()

    # Không đề xuất lại chính các phim người dùng đã đánh dấu yêu thích.
    for movie_id in valid_ids:
        similarities[movie_to_idx[movie_id]] = -1.0

    result = movies[["movieId", "title", "genres"]].copy()
    result["similarity"] = similarities
    result = result[result["similarity"] >= 0]
    result = result.sort_values(
        by=["similarity", "title"],
        ascending=[False, True],
    ).head(int(top_k))
    return result.reset_index(drop=True)
