import pandas as pd
import streamlit as st

from src.common import context, enrich, translate_genres, shorten_text
from pages_ui.movie_display import load_poster_data, show_movie_poster, navigate_to_movie_detail
from src.content_recommender import recommend_by_favorite_movies
from src.database import get_user_favorite_movie_ids
from src.user_ratings import get_user_ratings
from src.recommender_models import MODEL_LABELS, load_movielens_models, tensorflow_available


# Poster của các lô tiếp theo chỉ được tải khi người dùng yêu cầu xem thêm.
POSTER_BATCH_SIZE = 24
POSTER_SESSION_CACHE_KEY = "_recommendations_poster_cache_v1"


def _build_content_recommendations(seed_ids, exclude_ids, top_k=120):
    if not seed_ids:
        return pd.DataFrame(columns=["movieId", "title", "genres", "similarity"])

    return recommend_by_favorite_movies(seed_ids, top_k=top_k, exclude_movie_ids=exclude_ids)


def _normalize_tmdb_id(value):
    """Chuẩn hóa TMDb ID thành số nguyên dương; trả None nếu không hợp lệ."""
    try:
        numeric_id = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if not numeric_id > 0 or not numeric_id.is_integer():
        return None

    return int(numeric_id)


def _load_visible_poster_data(visible_movies):
    """Chỉ tải metadata poster cho các phim đang được render.

    Cache theo TMDb ID trong session để các lần rerun (ví dụ bấm Xem thêm)
    không gọi TMDb lại cho những phim đã xử lý. Giá trị None cũng được cache
    để tránh lặp request với phim không có poster.
    """
    if not isinstance(visible_movies, pd.DataFrame) or visible_movies.empty:
        return {}

    if "tmdbId" not in visible_movies.columns:
        return {}

    poster_cache = st.session_state.setdefault(POSTER_SESSION_CACHE_KEY, {})
    if not isinstance(poster_cache, dict):
        poster_cache = {}
        st.session_state[POSTER_SESSION_CACHE_KEY] = poster_cache

    visible_tmdb_ids = sorted(
        {
            tmdb_id
            for value in visible_movies["tmdbId"]
            if (tmdb_id := _normalize_tmdb_id(value)) is not None
        }
    )
    if not visible_tmdb_ids:
        return {}

    missing_ids = [
        tmdb_id for tmdb_id in visible_tmdb_ids if tmdb_id not in poster_cache
    ]

    if missing_ids:
        numeric_ids = pd.to_numeric(
            visible_movies["tmdbId"], errors="coerce"
        )
        movies_to_load = visible_movies.loc[numeric_ids.isin(missing_ids)]
        newly_loaded = load_poster_data(movies_to_load)

        # Cache cả kết quả không có poster để không gọi TMDb lặp lại.
        for tmdb_id in missing_ids:
            poster_cache[tmdb_id] = newly_loaded.get(tmdb_id)

    return {
        tmdb_id: poster_cache[tmdb_id]
        for tmdb_id in visible_tmdb_ids
        if poster_cache.get(tmdb_id)
    }


def _get_visible_page(user_id, section, movies, signature_extra=None):
    """Lấy lô phim hiện tại và trạng thái phân trang trong session."""
    movie_ids = tuple(
        int(movie_id)
        for movie_id in movies["movieId"].tolist()
    )
    signature = (movie_ids, signature_extra)
    state_key = f"_recommendations_page_{section}_{user_id}"

    page_state = st.session_state.get(state_key)
    if not isinstance(page_state, dict) or page_state.get("signature") != signature:
        page_state = {
            "signature": signature,
            "visible_count": min(POSTER_BATCH_SIZE, len(movies)),
        }
        st.session_state[state_key] = page_state

    visible_count = min(
        int(page_state.get("visible_count", POSTER_BATCH_SIZE)),
        len(movies),
    )
    return movies.head(visible_count), state_key, visible_count


def _render_load_more(user_id, section, state_key, total_count, visible_count):
    """Hiển thị nút tải lô kế tiếp sau danh sách phim."""
    st.caption(f"Đang hiển thị {visible_count}/{total_count} phim.")

    if visible_count >= total_count:
        return

    next_count = min(POSTER_BATCH_SIZE, total_count - visible_count)
    if st.button(
        f"Xem thêm {next_count} phim",
        key=f"recommendations_load_more_{section}_{user_id}",
        width="stretch",
    ):
        page_state = st.session_state.get(state_key, {})
        page_state["visible_count"] = min(
            visible_count + POSTER_BATCH_SIZE,
            total_count,
        )
        st.session_state[state_key] = page_state
        st.rerun()


def show_recommendations_page(user_id):
    if st.session_state.pop("scroll_to_top", False):
        st.iframe(
            """
            <script>
                const doc = window.parent.document;
                const scrollArea = doc.querySelector('[data-testid="stAppScrollToBottomContainer"]')
                    || doc.querySelector('[data-testid="stMain"]');
                if (scrollArea) scrollArea.scrollTo({top: 0, behavior: "instant"});
                window.parent.scrollTo(0, 0);
            </script>
            """,
            height=1,
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
                top_k=120,
            )
            score_kind = (
                "knn"
                if selected_model in {"User-based KNN", "Item-based KNN"}
                else "rating"
            )
        except Exception as exc:
            st.warning("Chưa thể chạy mô hình cộng tác; hệ thống chuyển sang TF-IDF.")
            st.caption(str(exc))

    if recommendations.empty:
        if seed_ids:
            recommendations = _build_content_recommendations(
                seed_ids, excluded_ids, top_k=120
            )
        elif not favorite_ids and not profile_ratings:
            recommendations = pd.DataFrame()

        if not recommendations.empty:
            score_kind = "content"

    if not recommendations.empty:
        # with st.expander("Debug số lượng phim gợi ý"):
        #     st.write("Mô hình:", selected_model)
        #     st.write("Tổng phim trong dataset:", len(movies))
        #     st.write("Số phim đã đánh giá:", len(rated_ids))
        #     st.write("Số phim yêu thích:", len(favorite_ids))
        #     st.write("Số phim bị loại:", len(excluded_ids))
        #     st.write("Số phim được mô hình đề xuất:", len(recommendations))
        
        tmdb_lookup = movies[["movieId", "tmdbId"]].drop_duplicates("movieId")
        recommendations = recommendations.merge(
            tmdb_lookup, on="movieId", how="left"
        )

        # Chỉ render và tải poster cho lô đầu tiên; các lô tiếp theo được tải
        # theo yêu cầu khi người dùng bấm nút "Xem thêm phim".
        visible_recommendations, page_state_key, visible_count = _get_visible_page(
            user_id,
            "recommendations",
            recommendations,
            signature_extra=selected_model,
        )
        poster_data = _load_visible_poster_data(visible_recommendations)

        if score_kind == "rating":
            st.caption(
                f"Mô hình: {selected_model}. Điểm rating dự đoán được suy ra từ lịch sử "
                "MovieLens và các rating bạn đã lưu trên MovieMatch."
            )
        elif score_kind == "knn":
            if selected_model == "User-based KNN":
                st.caption(
                    "Mô hình: User-based KNN. Xếp hạng theo tỷ lệ có trọng số của những "
                    "người dùng láng giềng đã đánh giá tích cực (từ 4/5); đây không phải rating dự đoán."
                )
            else:
                st.caption(
                    "Mô hình: Item-based KNN. Xếp hạng theo độ tương đồng cosine với "
                    "các phim bạn đã đánh giá tích cực; đây không phải rating dự đoán."
                )
        else:
            st.caption(
                "Mô hình: TF-IDF từ tên phim, thể loại và tags; xếp hạng bằng cosine similarity. "
                "Đây là phương án cold-start khi chưa có đủ rating."
            )

        columns = st.columns(3)
        for index, (_, movie) in enumerate(visible_recommendations.iterrows()):
            with columns[index % 3]:
                with st.container(border=True):
                    show_movie_poster(movie, poster_data, width=None)
                    st.write(f"**{shorten_text(movie['title'], max_chars=45)}**")
                    st.caption(shorten_text(translate_genres(movie["genres"]), max_chars=55))

                    if score_kind == "rating":
                        st.metric(
                            "Điểm rating dự đoán",
                            f"{float(movie['predicted_rating']):.2f}/5",
                        )
                    elif score_kind == "knn":
                        metric_label = (
                            "Tỷ lệ láng giềng đánh giá tích cực"
                            if selected_model == "User-based KNN"
                            else "Độ tương đồng với phim đã thích"
                        )
                        st.metric(
                            metric_label,
                            f"{float(movie['recommendation_score']) * 100:.1f}%",
                        )
                    else:
                        st.metric(
                            "Độ tương đồng nội dung",
                            f"{float(movie['similarity']) * 100:.1f}%",
                        )

                    movie_id = int(movie["movieId"])
                    if st.button(
                        "Xem chi tiết",
                        key=f"recommendation_detail_{user_id}_{movie_id}",
                        width="stretch",
                    ):
                        navigate_to_movie_detail(
                            movie_id, return_page="recommendations"
                        )

        _render_load_more(
            user_id,
            "recommendations",
            page_state_key,
            len(recommendations),
            visible_count,
        )
        return

    if not favorite_ids and not profile_ratings:
        st.info(
            "Bạn chưa lưu phim yêu thích hoặc chấm điểm phim. "
            "Hãy chọn vài phim yêu thích hoặc chấm ít nhất 3 phim để bắt đầu cá nhân hóa."
        )
        popular = (
            movie_data.sort_values(
                ["count", "score"], ascending=[False, False]
            )
            .head(120)
            .reset_index(drop=True)
        )
        visible_popular, page_state_key, visible_count = _get_visible_page(
            user_id,
            "popular",
            popular,
            signature_extra="popular",
        )
        poster_data = _load_visible_poster_data(visible_popular)

        st.subheader("Phim phổ biến để bắt đầu")
        columns = st.columns(3)
        for index, (_, movie) in enumerate(visible_popular.iterrows()):
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

                    movie_id = int(movie["movieId"])
                    if st.button(
                        "Xem chi tiết",
                        key=f"popular_detail_{user_id}_{movie_id}",
                        width="stretch",
                    ):
                        navigate_to_movie_detail(
                            movie_id, return_page="recommendations"
                        )

        _render_load_more(
            user_id,
            "popular",
            page_state_key,
            len(popular),
            visible_count,
        )

    else:
        st.info(
            "Chưa tìm được phim phù hợp với hồ sơ hiện tại. "
            "Hãy chấm thêm phim hoặc chọn thêm phim yêu thích."
        )
