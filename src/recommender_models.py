from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Iterable
import importlib.util
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.neighbors import NearestNeighbors
from src.common import MOVIES_FILE, RATINGS_FILE

MODEL_LABELS = {
    "User-based KNN": "user_knn",
    "Item-based KNN": "item_knn",
    "Truncated SVD": "truncated_svd",
    "Keras Embedding": "keras_embedding",
}


def tensorflow_available() -> bool:
    """Return whether TensorFlow is importable in the current environment."""
    return importlib.util.find_spec("tensorflow") is not None


class MovieLensModels:
    """Fit collaborative models once and personalize them for an external user."""

    def __init__(
        self,
        ratings: pd.DataFrame,
        movies: pd.DataFrame,
        n_components: int = 50,
        random_state: int = 69,
    ) -> None:
        required = {"userId", "movieId", "rating"}
        missing = required.difference(ratings.columns)
        if missing:
            raise ValueError(f"ratings.csv thiếu cột: {sorted(missing)}")
        if "movieId" not in movies.columns:
            raise ValueError("movies.csv cần có cột movieId.")

        clean = ratings[["userId", "movieId", "rating"]].copy()
        for column in ("userId", "movieId", "rating"):
            clean[column] = pd.to_numeric(clean[column], errors="coerce")
        clean = clean.dropna().copy()
        clean["userId"] = clean["userId"].astype(int)
        clean["movieId"] = clean["movieId"].astype(int)
        clean["rating"] = clean["rating"].astype(float)
        clean = clean.drop_duplicates(["userId", "movieId"], keep="last")
        if clean.empty:
            raise ValueError("Không có rating hợp lệ để huấn luyện mô hình.")

        self.ratings = clean.reset_index(drop=True)
        self.movies = movies.copy()
        self.movies["movieId"] = pd.to_numeric(
            self.movies["movieId"], errors="coerce"
        )
        self.movies = self.movies.dropna(subset=["movieId"]).copy()
        self.movies["movieId"] = self.movies["movieId"].astype(int)
        if "title" not in self.movies:
            self.movies["title"] = self.movies["movieId"].astype(str)
        if "genres" not in self.movies:
            self.movies["genres"] = ""

        # User-item matrix. NaN means no rating; the centered sparse form uses 0
        # only as a neutral value for fitting cosine neighbours and SVD.
        self.R = self.ratings.pivot_table(
            index="userId", columns="movieId", values="rating", aggfunc="mean"
        ).sort_index(axis=0).sort_index(axis=1)
        self.user_ids = self.R.index.to_numpy(dtype=np.int64)
        self.movie_ids = self.R.columns.to_numpy(dtype=np.int64)
        self.user_to_idx = {int(v): i for i, v in enumerate(self.user_ids)}
        self.movie_to_idx = {int(v): i for i, v in enumerate(self.movie_ids)}
        self.user_means = self.R.mean(axis=1)
        self.global_mean = float(self.ratings["rating"].mean())

        centered = self.R.sub(self.user_means, axis=0).fillna(0.0)
        self.user_matrix = csr_matrix(centered.to_numpy(dtype=np.float32))
        self.item_matrix = self.user_matrix.T.tocsr()

        self.user_knn = NearestNeighbors(metric="cosine", algorithm="brute")
        self.user_knn.fit(self.user_matrix)
        self.item_knn = NearestNeighbors(metric="cosine", algorithm="brute")
        self.item_knn.fit(self.item_matrix)

        smallest_dimension = min(self.user_matrix.shape)
        components = min(int(n_components), smallest_dimension - 1)
        if components < 1:
            raise ValueError("Cần ít nhất 2 người dùng và 2 phim để chạy Truncated SVD.")
        self.svd_model = TruncatedSVD(
            n_components=components, random_state=random_state
        )
        self.user_factors = self.svd_model.fit_transform(self.user_matrix)
        self.item_factors = self.svd_model.components_.T
        self._keras_assets = None

    @classmethod
    def from_csv(cls) -> "MovieLensModels":
        if not RATINGS_FILE.exists() or not MOVIES_FILE.exists():
            raise FileNotFoundError(
                "Không tìm thấy MovieLens. Cần có data/ml-latest-small/ratings.csv "
                "và movies.csv."
            )
        return cls(pd.read_csv(RATINGS_FILE), pd.read_csv(MOVIES_FILE))

    @staticmethod
    def _normalize_profile(profile_ratings: Mapping[int, float]) -> tuple[list[int], np.ndarray]:
        if not isinstance(profile_ratings, Mapping):
            raise TypeError("profile_ratings phải là dict {movieId: rating}.")
        movie_ids: list[int] = []
        values: list[float] = []
        for movie_id, rating in profile_ratings.items():
            try:
                movie_id, rating = int(movie_id), float(rating)
            except (TypeError, ValueError):
                continue
            if np.isfinite(rating) and 0.5 <= rating <= 5.0:
                movie_ids.append(movie_id)
                values.append(rating)
        return movie_ids, np.asarray(values, dtype=np.float64)

    def _score_user_knn(
        self,
        rated_indices: list[int],
        values: np.ndarray,
        k: int,
        positive_threshold: float = 4.0,
    ) -> np.ndarray:
        """
        Return a neighbor-vote ranking score, not a predicted rating.

        For each unseen movie, the score is the similarity-weighted share of
        neighboring users who rated that movie >= positive_threshold.
        """
        profile_mean = float(values.mean())
        profile_vector = np.zeros(len(self.movie_ids), dtype=np.float32)
        profile_vector[rated_indices] = values - profile_mean
        if np.linalg.norm(profile_vector) < 1e-8:
            return np.zeros(len(self.movie_ids), dtype=np.float64)

        n_neighbors = min(max(int(k), 1), len(self.user_ids))
        distances, indices = self.user_knn.kneighbors(
            csr_matrix(profile_vector.reshape(1, -1)),
            n_neighbors=n_neighbors,
        )
        neighbor_indices = indices.ravel()
        similarities = np.clip(1.0 - distances.ravel(), 0.0, None)

        # Discount neighbors that overlap with too few items in this profile.
        overlap = (
            self.R.iloc[neighbor_indices, rated_indices]
            .notna()
            .sum(axis=1)
            .to_numpy()
        )
        similarities *= overlap / (overlap + 5.0)
        keep = (overlap >= 2) & (similarities > 0)
        if not keep.any():
            return np.zeros(len(self.movie_ids), dtype=np.float64)

        neighbor_indices = neighbor_indices[keep]
        similarities = similarities[keep]
        neighbor_ratings = self.R.iloc[neighbor_indices].to_numpy(dtype=float)

        observed = np.isfinite(neighbor_ratings)
        positive = observed & (neighbor_ratings >= float(positive_threshold))
        positive_weight = (similarities[:, None] * positive).sum(axis=0)
        observed_weight = (similarities[:, None] * observed).sum(axis=0)

        scores = np.zeros(len(self.movie_ids), dtype=np.float64)
        valid = observed_weight > 0
        scores[valid] = positive_weight[valid] / observed_weight[valid]
        return np.clip(scores, 0.0, 1.0)

    def _score_item_knn(
        self,
        rated_indices: list[int],
        values: np.ndarray,
        k: int,
        positive_threshold: float = 4.0,
    ) -> np.ndarray:
        """
        Return a content-free item-neighborhood similarity ranking score.

        Candidate movies are ranked by their weighted mean cosine similarity
        to the movies this user rated positively. No rating is inferred.
        """
        liked_mask = values >= float(positive_threshold)
        liked_indices = np.asarray(rated_indices, dtype=int)[liked_mask]
        liked_values = np.asarray(values, dtype=float)[liked_mask]
        scores = np.full(len(self.movie_ids), np.nan, dtype=np.float64)

        if liked_indices.size == 0:
            return scores

        # Stronger positive ratings give their liked movies slightly more
        # influence, while the returned value remains a similarity score.
        preference_weights = np.maximum(liked_values - 3.0, 0.0)
        numerator = np.zeros(len(self.movie_ids), dtype=np.float64)
        denominator = np.zeros(len(self.movie_ids), dtype=np.float64)

        n_neighbors = min(max(int(k) + 1, 2), len(self.movie_ids))
        for item_idx, preference_weight in zip(liked_indices, preference_weights):
            distances, indices = self.item_knn.kneighbors(
                self.item_matrix[item_idx],
                n_neighbors=n_neighbors,
            )
            similarities = np.clip(1.0 - distances.ravel(), 0.0, None)

            for neighbor_idx, similarity in zip(indices.ravel(), similarities):
                if neighbor_idx == item_idx or similarity <= 0:
                    continue
                numerator[neighbor_idx] += similarity * preference_weight
                denominator[neighbor_idx] += preference_weight

        valid = denominator > 0
        scores[valid] = numerator[valid] / denominator[valid]
        return np.clip(scores, 0.0, 1.0)

    def _score_truncated_svd(self, rated_indices: list[int], values: np.ndarray, reg: float = 0.5) -> np.ndarray:
        profile_mean = float(values.mean())
        item_vectors = self.item_factors[np.asarray(rated_indices, dtype=int)]
        target = values - profile_mean
        gram = item_vectors.T @ item_vectors
        latent = np.linalg.solve(
            gram + float(reg) * np.eye(gram.shape[0]),
            item_vectors.T @ target,
        )
        scores = profile_mean + self.item_factors @ latent
        return np.clip(scores, 0.5, 5.0)

    def _fit_keras_assets(self, epochs: int = 12) -> dict:
        if self._keras_assets is not None:
            return self._keras_assets
        try:
            import tensorflow as tf
            from keras import layers
        except ImportError as exc:
            raise RuntimeError(
                "Keras Embedding cần TensorFlow. Cài bằng: "
                "pip install -r requirements-optional-keras.txt"
            ) from exc

        tf.keras.utils.set_random_seed(69)
        user_map = self.user_to_idx
        movie_map = self.movie_to_idx
        user_idx = self.ratings["userId"].map(user_map).to_numpy(dtype=np.int32).reshape(-1, 1)
        movie_idx = self.ratings["movieId"].map(movie_map).to_numpy(dtype=np.int32).reshape(-1, 1)
        y = self.ratings["rating"].to_numpy(dtype=np.float32)
        embedding_dim = min(32, max(8, len(self.user_ids) // 10))
        regularizer = tf.keras.regularizers.l2(1e-6)

        user_input = tf.keras.Input(shape=(1,), dtype="int32", name="user_id")
        movie_input = tf.keras.Input(shape=(1,), dtype="int32", name="movie_id")
        user_layer = layers.Embedding(
            len(user_map), embedding_dim, embeddings_regularizer=regularizer,
            name="user_embedding",
        )
        movie_layer = layers.Embedding(
            len(movie_map), embedding_dim, embeddings_regularizer=regularizer,
            name="movie_embedding",
        )
        user_bias_layer = layers.Embedding(len(user_map), 1, name="user_bias_embedding")
        movie_bias_layer = layers.Embedding(len(movie_map), 1, name="movie_bias_embedding")

        user_vector = layers.Flatten()(user_layer(user_input))
        movie_vector = layers.Flatten()(movie_layer(movie_input))
        dot = layers.Dot(axes=1)([user_vector, movie_vector])
        user_bias = layers.Flatten()(user_bias_layer(user_input))
        movie_bias = layers.Flatten()(movie_bias_layer(movie_input))
        baseline = layers.Rescaling(1.0, offset=self.global_mean)(dot)
        output = layers.Add()([baseline, user_bias, movie_bias])
        model = tf.keras.Model([user_input, movie_input], output)
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mse")
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=2, restore_best_weights=True
            )
        ] if len(y) >= 20 else []
        model.fit(
            [user_idx, movie_idx], y,
            epochs=int(epochs), batch_size=4096,
            validation_split=0.1 if len(y) >= 20 else 0.0,
            callbacks=callbacks, shuffle=True, verbose=0,
        )

        self._keras_assets = {
            "movie_embeddings": movie_layer.get_weights()[0],
            "movie_bias": movie_bias_layer.get_weights()[0].reshape(-1),
            "global_mean": self.global_mean,
            "model": model,
        }
        return self._keras_assets

    def _score_keras_embedding(self, rated_indices: list[int], values: np.ndarray) -> np.ndarray:
        assets = self._fit_keras_assets()
        profile_mean = float(values.mean())
        movie_embeddings = assets["movie_embeddings"]
        movie_bias = assets["movie_bias"]
        selected_vectors = movie_embeddings[np.asarray(rated_indices, dtype=int)]
        target = values - float(assets["global_mean"]) - movie_bias[np.asarray(rated_indices, dtype=int)]

        design = np.column_stack([selected_vectors, np.ones(len(selected_vectors))])
        reg = np.eye(design.shape[1], dtype=np.float64) * 0.1
        reg[-1, -1] = 1e-6
        coefficients = np.linalg.solve(design.T @ design + reg, design.T @ target)
        latent_user = coefficients[:-1]
        user_bias = float(coefficients[-1])
        scores = (
            float(assets["global_mean"])
            + movie_bias
            + movie_embeddings @ latent_user
            + user_bias
        )
        return np.clip(scores, 0.5, 5.0)

    def recommend(
        self,
        profile_ratings: Mapping[int, float],
        model: str = "truncated_svd",
        exclude_movie_ids: Iterable[int] | None = None,
        top_k: int = 12,
        k: int = 20,
    ) -> pd.DataFrame:
        """
        Recommend unseen movies for an external account's {movieId: rating} profile.

        KNN methods return a recommendation/similarity score for ranking only.
        SVD and Keras Embedding return predicted_rating estimates.
        """
        profile_ids, values = self._normalize_profile(profile_ratings)
        if len(profile_ids) < 2:
            raise ValueError("Cần ít nhất 2 điểm đánh giá hợp lệ để dùng lọc cộng tác.")
        known = [
            (movie_id, value)
            for movie_id, value in zip(profile_ids, values)
            if movie_id in self.movie_to_idx
        ]
        if len(known) < 2:
            raise ValueError("Các phim đã chấm chưa có đủ trong dữ liệu MovieLens.")
        rated_indices = [self.movie_to_idx[mid] for mid, _ in known]
        known_values = np.asarray([value for _, value in known], dtype=np.float64)

        method = MODEL_LABELS.get(model, model)
        is_knn = method in {"user_knn", "item_knn"}
        if method == "user_knn":
            scores = self._score_user_knn(rated_indices, known_values, k)
        elif method == "item_knn":
            scores = self._score_item_knn(rated_indices, known_values, k)
        elif method == "truncated_svd":
            scores = self._score_truncated_svd(rated_indices, known_values)
        elif method == "keras_embedding":
            scores = self._score_keras_embedding(rated_indices, known_values)
        else:
            raise ValueError(f"Mô hình không được hỗ trợ: {model}")

        excluded = {int(value) for value in (exclude_movie_ids or [])}
        excluded.update(int(movie_id) for movie_id, _ in known)
        rows = []
        for movie_id, score in zip(self.movie_ids, scores):
            movie_id = int(movie_id)
            score = float(score)
            if movie_id in excluded or not np.isfinite(score):
                continue
            # A KNN recommendation must have positive neighbor support/similarity.
            if is_knn and score <= 0:
                continue
            rows.append((movie_id, score))

        score_column = "recommendation_score" if is_knn else "predicted_rating"
        empty_columns = ["movieId", "title", "genres", score_column]
        if not rows:
            return pd.DataFrame(columns=empty_columns)

        ranked = pd.DataFrame(rows, columns=["movieId", score_column])
        ranked = ranked.merge(
            self.movies[["movieId", "title", "genres"]].drop_duplicates("movieId"),
            on="movieId", how="left",
        )
        ranked["title"] = ranked["title"].fillna(ranked["movieId"].astype(str))
        ranked["genres"] = ranked["genres"].fillna("")
        ranked = ranked.sort_values(
            [score_column, "title"], ascending=[False, True]
        ).head(max(1, int(top_k)))
        return ranked.reset_index(drop=True)


def _build_models() -> MovieLensModels:
    return MovieLensModels.from_csv()


try:
    import streamlit as _st
    load_movielens_models = _st.cache_resource(
        show_spinner="Đang huấn luyện các mô hình lọc cộng tác trên MovieLens..."
    )(_build_models)
except ImportError:
    load_movielens_models = lru_cache(maxsize=1)(_build_models)
