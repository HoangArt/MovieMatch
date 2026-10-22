import pandas as pd
import streamlit as st
from services.tmdb_api import fetch_all_posters, get_tmdb_api_key

def load_poster_data(movies, *, spinner_text="Đang tải poster phim từ TMDB...", warn_if_missing_key=False):
    """Tải poster cho một DataFrame phim và trả về dictionary theo tmdbId.

    Hàm được dùng chung ở trang chủ và trang gợi ý để tránh lặp lại
    logic lấy API key, lọc ID và gọi TMDB.
    """
    if movies is None or movies.empty or "tmdbId" not in movies.columns:
        return {}

    api_key = get_tmdb_api_key()
    if not api_key:
        if warn_if_missing_key:
            st.warning(
                "Chưa cấu hình TMDB_API_KEY. Danh sách phim và điểm đánh giá "
                "vẫn hiển thị, nhưng poster từ TMDB chưa tải được."
            )
        return {}

    # Lọc ID rỗng/không hợp lệ và giữ thứ tự, đồng thời loại ID trùng.
    tmdb_ids = []
    seen_ids = set()
    for value in movies["tmdbId"]:
        try:
            if pd.isna(value):
                continue
            tmdb_id = int(float(value))
            if tmdb_id > 0 and tmdb_id not in seen_ids:
                tmdb_ids.append(tmdb_id)
                seen_ids.add(tmdb_id)
        except (TypeError, ValueError, OverflowError):
            continue

    if not tmdb_ids:
        return {}

    if spinner_text:
        with st.spinner(spinner_text):
            return fetch_all_posters(tmdb_ids, api_key)

    return fetch_all_posters(tmdb_ids, api_key)


def show_movie_poster(movie, poster_data, width=150):
    """Hiển thị poster của một dòng phim; dùng placeholder nếu thiếu ảnh."""
    tmdb_id = movie.get("tmdbId")
    poster_url = None

    try:
        if pd.notna(tmdb_id):
            movie_info = (poster_data or {}).get(int(float(tmdb_id)), {})
            poster_url = movie_info.get("poster_url")
    except (TypeError, ValueError, OverflowError):
        poster_url = None

    if poster_url:
        if width is None:
            st.image(poster_url, use_container_width=True)
        else:
            st.image(poster_url, width=width)
    else:
        st.markdown(
            """
            <div style="
                width: 100%;
                aspect-ratio: 2 / 3;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #202027;
                color: #a5a5b0;
                border-radius: 8px;
                font-size: 42px;
            ">Không có ảnh</div>
            """,
            unsafe_allow_html=True,
            # TO-DO: Chỉnh postere không có ảnh
        )
