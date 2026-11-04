import pandas as pd
import streamlit as st

from src.common import context, enrich, translate_genres, shorten_text
from pages_ui.movie_display import load_poster_data, show_movie_poster
from src.content_recommender import recommend_by_favorite_movies
from src.database import get_user_favorite_movie_ids
from src.user_ratings import get_user_ratings
from src.recommender_models import (
    MODEL_LABELS,
    load_movielens_models,
    tensorflow_available,
)


def _build_content_recommendations(seed_ids, exclude_ids, top_k=12):
    if not seed_ids:
        return pd.DataFrame(columns=["movieId", "title", "genres", "similarity"])
    result = recommend_by_favorite_movies(seed_ids, top_k=top_k * 3)
    if result.empty:
        return result
    return result[~result["movieId"].isin(set(exclude_ids))].head(top_k).reset_index(drop=True)


def show_recommendations_page(user_id):
    """Show content-based cold-start or collaborative recommendations."""
    if st.session_state.pop("scroll_to_top", False):
        st.components.v1.html(
            """
            <script>
                const doc = window.parent.document;
                const scrollArea = doc.querySelector('[data-testid="stAppScrollToBottomContainer"]')
                    || doc.querySelector('[data-testid="stMain"]');
                if (scrollArea) scrollArea.scrollTo({top: 0, behavior: "instant"});
                window.parent.scrollTo(0, 0);
            </script>
            """,
            height=0,
        )

    st.title("Gợi ý phim dành cho bạn")
    username = st.session_state.get("username")
    favorite_ids = get_user_favorite_movie_ids(user_id)
    rating_rows = get_user_ratings(username)
    profile_ratings = {
        int(row["movie_id"]): float(row["rating"])
        for row in rating_rows
    }
    rated_ids = set(profile_ratings)
    excluded_ids = rated_ids | {int(value) for value in favorite_ids}

    model_options = [
        "Content-based (TF-IDF)",
        "User-based KNN",
        "Item-based KNN",
        "Truncated SVD",
        "Keras Embedding",
    ]
    selected_model = st.selectbox(
        "Chọn mô hình gợi ý",
        model_options,
        help=(
            "Content-based phù hợp với tài khoản mới. Các mô hình cộng tác dùng "
            "điểm bạn đã chấm và lịch sử rating MovieLens."
        ),
    )
    st.caption(
        f"Bạn đã chấm {len(profile_ratings)} phim. "
        "Tài khoản MovieMatch được cá nhân hóa riêng, không dùng userId MovieLens làm userId tài khoản."
    )
    if not tensorflow_available():
        st.info(
            "Keras Embedding cần cài TensorFlow: "
            "pip install -r requirements-optional-keras.txt"
        )

    movies, ratings, _ = context()
    movie_data = enrich(movies, ratings)
    seed_ids = list(favorite_ids)
    if not seed_ids:
        seed_ids = [
            int(movie_id)
            for movie_id, rating in profile_ratings.items()
            if rating >= 4.0
        ]

    if favorite_ids:
        selected = movie_data[movie_data["movieId"].isin(favorite_ids)]
        st.write("Dựa trên các phim bạn yêu thích:")
        st.caption(" · ".join(selected["title"].tolist()))
    elif profile_ratings:
        st.write("Dựa trên lịch sử đánh giá của bạn:")

    recommendations = pd.DataFrame()
    score_kind = "content"
    chosen_cf = selected_model != "Content-based (TF-IDF)"

    if chosen_cf and len(profile_ratings) < 3:
        st.warning(
            "Cần ít nhất 3 phim đã chấm điểm để dùng mô hình cộng tác ổn định hơn. "
            "Tạm thời hệ thống chuyển sang TF-IDF để xử lý cold-start."
        )
    elif chosen_cf:
        try:
            if selected_model == "Keras Embedding" and not tensorflow_available():
                raise RuntimeError(
                    "Keras Embedding cần TensorFlow. Cài bằng: "
                    "pip install -r requirements-optional-keras.txt"
                )
            recommender = load_movielens_models()
            recommendations = recommender.recommend(
                profile_ratings,
                model=MODEL_LABELS[selected_model],
                exclude_movie_ids=excluded_ids,
                top_k=12,
            )
            score_kind = "rating"
        except Exception as exc:
            st.warning("Chưa thể chạy mô hình cộng tác; hệ thống chuyển sang TF-IDF.")
            st.caption(str(exc))

    if recommendations.empty:
        if seed_ids:
            recommendations = _build_content_recommendations(
                seed_ids, excluded_ids, top_k=12
            )
        elif not favorite_ids and not profile_ratings:
            recommendations = pd.DataFrame()

        if not recommendations.empty:
            score_kind = "content"

    if not recommendations.empty:
        tmdb_lookup = movies[["movieId", "tmdbId"]].drop_duplicates("movieId")
        recommendations = recommendations.merge(
            tmdb_lookup, on="movieId", how="left"
        )
        poster_data = load_poster_data(recommendations)

        if score_kind == "rating":
            st.caption(
                f"Mô hình: {selected_model}. Điểm dự đoán được suy ra từ lịch sử MovieLens "
                "và các rating bạn đã lưu trên MovieMatch."
            )
        else:
            st.caption(
                "Mô hình: TF-IDF từ tên phim, thể loại và tags; xếp hạng bằng cosine similarity. "
                "Đây là phương án cold-start khi chưa có đủ rating."
            )

        columns = st.columns(3)
        for index, (_, movie) in enumerate(recommendations.iterrows()):
            with columns[index % 3]:
                with st.container(border=True):
                    show_movie_poster(movie, poster_data, width=None)
                    st.write(f"**{shorten_text(movie['title'], max_chars=45)}**")
                    st.caption(shorten_text(translate_genres(movie["genres"]), max_chars=55))
                    if score_kind == "rating":
                        st.metric(
                            "Điểm dự đoán",
                            f"{float(movie['predicted_rating']):.2f}/5",
                        )
                    else:
                        st.metric(
                            "Độ tương đồng nội dung",
                            f"{float(movie['similarity']) * 100:.1f}%",
                        )
        return

    if not favorite_ids and not profile_ratings:
        st.info(
            "Bạn chưa lưu phim yêu thích hoặc chấm điểm phim. "
            "Hãy chọn vài phim yêu thích hoặc chấm ít nhất 3 phim để bắt đầu cá nhân hóa."
        )
        popular = movie_data.sort_values(
            ["count", "score"], ascending=[False, False]
        ).head(12)
        poster_data = load_poster_data(popular)
        st.subheader("Phim phổ biến để bắt đầu")
        columns = st.columns(3)
        for index, (_, movie) in enumerate(popular.iterrows()):
            with columns[index % 3]:
                with st.container(border=True):
                    show_movie_poster(movie, poster_data, width=None)
                    st.write(f"**{movie['title']}**")
                    st.caption(translate_genres(movie["genres"]))
                    count = movie.get("count", 0)
                    if pd.notna(count) and int(count) > 0:
                        st.caption(
                            f":star: {float(movie['mean']):.1f}/5 · {int(count):,} lượt"
                        )
    else:
        st.info(
            "Chưa tìm được phim phù hợp với hồ sơ hiện tại. "
            "Hãy chấm thêm phim hoặc chọn thêm phim yêu thích."
        )