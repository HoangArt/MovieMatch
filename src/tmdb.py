import os

import requests
import streamlit as st

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p"


# 1. LẤY API KEY
def get_api_key():
    """
    Đọc API key từ Streamlit Secrets.
    Có thể dùng biến môi trường làm phương án dự phòng.
    """

    try:
        api_key = st.secrets.get("TMDB_API_KEY")
    except Exception:
        api_key = None

    return api_key or os.getenv("TMDB_API_KEY")


# 2. LẤY THÔNG TIN PHIM TỪ TMDB
@st.cache_data(
    ttl=3600,
    max_entries=500,
    show_spinner=False,
)
def get_movie_info(tmdb_id, language="vi-VN"):
    """
    Lấy thông tin một bộ phim từ TMDB.

    Cache kết quả trong 1 giờ để tránh
    gọi API lặp lại khi Streamlit chạy lại.
    """

    api_key = get_api_key()

    # Nếu chưa cấu hình API key,
    # trang chủ vẫn có thể hiển thị danh sách phim.
    if not api_key or tmdb_id is None:
        return {}

    try:
        response = requests.get(
            f"{TMDB_BASE_URL}/movie/{int(tmdb_id)}",
            params={
                "api_key": api_key,
                "language": language,
            },
            timeout=8,
        )

        response.raise_for_status()
        data = response.json()

        backdrop_path = data.get("backdrop_path")
        poster_path = data.get("poster_path")

        return {
            "backdrop": (
                f"{TMDB_IMAGE_URL}/w1280{backdrop_path}"
                if backdrop_path
                else None
            ),
            "poster": (
                f"{TMDB_IMAGE_URL}/w500{poster_path}"
                if poster_path
                else None
            ),
            "overview": data.get("overview", ""),
        }

    except (requests.RequestException, ValueError, TypeError):
        return {}


# 3. LẤY ẢNH NỀN
def get_movie_backdrop(tmdb_id):
    info = get_movie_info(tmdb_id)

    return info.get("backdrop")

# 4. LẤY POSTER
def get_movie_poster(tmdb_id):
    info = get_movie_info(tmdb_id)

    return info.get("poster")

# 5. LẤY MÔ TẢ TIẾNG VIỆT
def get_vietnamese_overview(tmdb_id):
    info = get_movie_info(
        tmdb_id,
        language="vi-VN",
    )

    overview = info.get("overview", "")

    # Nếu TMDB không có mô tả tiếng Việt,
    # thử lấy mô tả tiếng Anh.
    if not overview:
        english_info = get_movie_info(
            tmdb_id,
            language="en-US",
        )

        overview = english_info.get("overview", "")

    return overview