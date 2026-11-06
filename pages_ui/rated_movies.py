import pandas as pd
import streamlit as st

from pages_ui.movie_display import load_poster_data, navigate_to_movie_detail, show_movie_poster
from src.common import context, shorten_text, translate_genres
from src.user_ratings import get_user_ratings


# Hiển thị từng lô để không tải poster của toàn bộ danh sách cùng lúc.
RATED_MOVIES_BATCH_SIZE = 6
RATED_POSTER_SESSION_CACHE_KEY = "_rated_movies_poster_cache_v1"


def _normalize_tmdb_id(value):
    """Chuẩn hóa TMDb ID; trả về None nếu giá trị không hợp lệ."""
    try:
        numeric_id = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if numeric_id <= 0 or not numeric_id.is_integer():
        return None

    return int(numeric_id)


def _load_visible_poster_data(visible_movies):
    """Chỉ tải poster cho lô đang hiển thị và giữ cache trong session."""
    if not isinstance(visible_movies, pd.DataFrame) or visible_movies.empty:
        return {}

    if "tmdbId" not in visible_movies.columns:
        return {}

    poster_cache = st.session_state.setdefault(
        RATED_POSTER_SESSION_CACHE_KEY, {}
    )
    if not isinstance(poster_cache, dict):
        poster_cache = {}
        st.session_state[RATED_POSTER_SESSION_CACHE_KEY] = poster_cache

    visible_tmdb_ids = sorted(
        {
            tmdb_id
            for value in visible_movies["tmdbId"]
            if (tmdb_id := _normalize_tmdb_id(value)) is not None
        }
    )
    missing_ids = [
        tmdb_id for tmdb_id in visible_tmdb_ids if tmdb_id not in poster_cache
    ]

    if missing_ids:
        numeric_ids = pd.to_numeric(
            visible_movies["tmdbId"], errors="coerce"
        )
        movies_to_load = visible_movies.loc[numeric_ids.isin(missing_ids)]
        newly_loaded = load_poster_data(movies_to_load)

        # Cache cả trường hợp không tìm thấy poster để không gọi TMDb lặp lại.
        for tmdb_id in missing_ids:
            poster_cache[tmdb_id] = newly_loaded.get(tmdb_id)

    return {
        tmdb_id: poster_cache[tmdb_id]
        for tmdb_id in visible_tmdb_ids
        if poster_cache.get(tmdb_id)
    }


def _get_visible_page(user_id, rated_movies):
    """Khôi phục số phim đang hiển thị; tự đặt lại khi danh sách thay đổi."""
    signature = tuple(
        (
            int(row.movieId),
            float(row.rating),
            str(row.updated_at),
        )
        for row in rated_movies[["movieId", "rating", "updated_at"]].itertuples(
            index=False
        )
    )
    state_key = f"_rated_movies_page_{int(user_id)}"
    page_state = st.session_state.get(state_key)

    if not isinstance(page_state, dict) or page_state.get("signature") != signature:
        page_state = {
            "signature": signature,
            "visible_count": min(RATED_MOVIES_BATCH_SIZE, len(rated_movies)),
        }
        st.session_state[state_key] = page_state

    visible_count = min(
        int(page_state.get("visible_count", RATED_MOVIES_BATCH_SIZE)),
        len(rated_movies),
    )
    return rated_movies.head(visible_count), state_key, visible_count


def _render_load_more(user_id, state_key, total_count, visible_count):
    """Tăng số phim hiển thị theo từng lô khi người dùng yêu cầu."""
    st.caption(f"Đang hiển thị {visible_count}/{total_count} phim đã đánh giá.")

    if visible_count >= total_count:
        return

    next_count = min(
        RATED_MOVIES_BATCH_SIZE,
        total_count - visible_count,
    )
    if st.button(
        f"Xem thêm {next_count} phim",
        key=f"rated_movies_load_more_{user_id}",
        width="stretch",
    ):
        page_state = st.session_state.get(state_key, {})
        page_state["visible_count"] = min(
            visible_count + RATED_MOVIES_BATCH_SIZE,
            total_count,
        )
        st.session_state[state_key] = page_state
        st.rerun()


def _build_rated_movies(username):
    """Ghép rating tài khoản hiện tại với thông tin phim MovieLens."""
    rating_rows = get_user_ratings(username)
    if not rating_rows:
        return pd.DataFrame(
            columns=["movieId", "rating", "updated_at", "title", "genres", "tmdbId"]
        )

    user_ratings = pd.DataFrame(rating_rows)
    user_ratings["movieId"] = pd.to_numeric(
        user_ratings["movie_id"], errors="coerce"
    )
    user_ratings["rating"] = pd.to_numeric(
        user_ratings["rating"], errors="coerce"
    )
    user_ratings = user_ratings.dropna(subset=["movieId", "rating"]).copy()
    user_ratings["movieId"] = user_ratings["movieId"].astype(int)

    movies, _, _ = context()
    movie_columns = ["movieId", "title", "genres", "tmdbId"]
    movie_info = movies[movie_columns].drop_duplicates("movieId")

    rated_movies = user_ratings.merge(
        movie_info,
        on="movieId",
        how="left",
        validate="many_to_one",
    )
    rated_movies["title"] = rated_movies["title"].fillna(
        rated_movies["movieId"].map(lambda movie_id: f"Phim #{movie_id}")
    )
    rated_movies["genres"] = rated_movies["genres"].fillna("")
    rated_movies["updated_at"] = rated_movies["updated_at"].fillna("")

    # Rating mới cập nhật được hiển thị trước.
    rated_movies["_sort_time"] = pd.to_datetime(
        rated_movies["updated_at"], errors="coerce", utc=True
    )
    rated_movies = rated_movies.sort_values(
        "_sort_time", ascending=False, na_position="last"
    ).drop(columns="_sort_time")

    return rated_movies.reset_index(drop=True)


def show_rated_movies_page(user_id):
    """Hiển thị danh sách phim và điểm mà tài khoản hiện tại đã đánh giá."""
    username = st.session_state.get("username")

    st.title("Phim đã đánh giá")
    st.write(
        "Danh sách phim bạn đã chấm điểm trên MovieMatch. "
        "Phim được sắp xếp theo thời gian cập nhật đánh giá gần nhất."
    )

    if not username:
        st.info("Vui lòng đăng nhập để xem danh sách phim đã đánh giá.")
        return

    rated_movies = _build_rated_movies(username)
    total_count = len(rated_movies)

    if rated_movies.empty:
        st.info(
            "Bạn chưa đánh giá phim nào. Hãy tìm một bộ phim, mở trang chi tiết "
            "và gửi đánh giá đầu tiên để danh sách xuất hiện tại đây."
        )
        if st.button("Khám phá phim", key=f"rated_movies_explore_{user_id}"):
            st.session_state["main_navigation"] = "Tìm kiếm"
            st.rerun()
        return

    average_rating = float(rated_movies["rating"].mean())
    st.metric("Số phim đã đánh giá", f"{total_count:,}")
    st.caption(f"Điểm trung bình bạn đã chấm: {average_rating:.2f}/5 sao")

    visible_movies, state_key, visible_count = _get_visible_page(
        user_id, rated_movies
    )
    poster_data = _load_visible_poster_data(visible_movies)

    columns = st.columns(3)
    for index, (_, movie) in enumerate(visible_movies.iterrows()):
        movie_id = int(movie["movieId"])

        with columns[index % 3]:
            with st.container(border=True):
                show_movie_poster(movie, poster_data, width=None)
                st.write(f"**{shorten_text(movie['title'], max_chars=42)}**")

                genres = translate_genres(movie.get("genres", ""))
                if genres:
                    st.caption(shorten_text(genres, max_chars=58))

                st.metric("Điểm bạn đã chấm", f":star: {float(movie['rating']):.1f}/5")

                updated_at = pd.to_datetime(
                    movie.get("updated_at"), errors="coerce", utc=True
                )
                if pd.notna(updated_at):
                    local_time = updated_at.tz_convert("Asia/Ho_Chi_Minh")
                    st.caption(f"Cập nhật: {local_time.strftime('%d/%m/%Y %H:%M')}")

                if st.button(
                    "Xem chi tiết",
                    key=f"rated_movie_detail_{user_id}_{movie_id}",
                    width="stretch",
                ):
                    navigate_to_movie_detail(
                        movie_id,
                        return_page="rated_movies",
                    )

    _render_load_more(user_id, state_key, total_count, visible_count)