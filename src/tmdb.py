import streamlit as st
import os
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p"

# ==================================================
# 1. LẤY TMDB API KEY
# ==================================================


def get_tmdb_api_key():
    """
    Lấy API key từ biến môi trường hoặc secrets.toml
    """

    # Ưu tiên API key trong biến môi trường.
    api_key = os.getenv("TMDB_API_KEY", "")
    if api_key:
        return api_key

    # Nếu không có, đọc từ Streamlit secrets.
    try:
        api_key = st.secrets.get("TMDB_API_KEY", "")
    except Exception:
        api_key = ""

    return api_key


# ==================================================
# 2. LẤY THÔNG TIN MỘT PHIM TỪ TMDB
# ==================================================
@st.cache_data(ttl=24*60*60, show_spinner=False)
def fetch_tmdb_movie(tmdb_id, api_key, language="vi-VN"):
    """
    Gọi TMDB API để lấy thông tin một bộ phim. 
    Cache kết quả trong 24 giờ.
    """
    if not api_key or tmdb_id is None:
        return {}

    try:
        tmdb_id = int(tmdb_id)

        if tmdb_id <= 0:
            return {}

        response = requests.get(
            f"{TMDB_BASE_URL}/movie/{tmdb_id}",
            params={
                "api_key": api_key,
                "language": language,
            },
            timeout=8,
        )

        response.raise_for_status()
        movie_info = response.json()

        poster_path = movie_info.get("poster_path")
        backdrop_path = movie_info.get("backdrop_path")

        # Lấy đường dẫn poster và ảnh nền
        poster_url = f"{TMDB_IMAGE_URL}/w342{poster_path}" if poster_path else None
        poster = f"{TMDB_IMAGE_URL}/w500{poster_path}" if poster_path else None
        backdrop = f"{TMDB_IMAGE_URL}/w1280{backdrop_path}" if backdrop_path else None

        # Trả về các thông tin cần thiết cho giao diện.
        return {
            "poster_url": poster_url,
            "poster": poster,
            "backdrop": backdrop,
            "tmdb_title": movie_info.get("title", ""),
            "overview": movie_info.get("overview", ""),
            "release_date": movie_info.get("release_date", ""),
            "runtime": movie_info.get("runtime"),
            "tmdb_vote_average": movie_info.get("vote_average"),
            "original_language": movie_info.get(
                "original_language", ""
            ),
            "tagline": movie_info.get("tagline", ""),
            "tmdb_genres": [
                genre["name"]
                for genre in movie_info.get("genres", [])
            ],
            "homepage": movie_info.get("homepage", ""),
        }

    except (requests.RequestException, ValueError, TypeError, OverflowError):
        return {}

# ==================================================
# 3. LẤY THÔNG TIN NHIỀU PHIM
# ==================================================


def fetch_all_posters(tmdb_ids, api_key):
    """
    Lấy thông tin Poster từ TMDB của nhiều phim.

    Các yêu cầu được thực hiện song song.
    Kết quả trả về là dictionary có tmdbId làm khóa.
    """

    if not api_key or tmdb_ids is None:
        return {}

    # Lọc ID trống, ID không hợp lệ và ID trùng nhau.
    valid_ids = set()

    for value in tmdb_ids:
        try:
            if pd.isna(value):
                continue

            numeric_id = float(value)

            if (numeric_id > 0 and numeric_id.is_integer()):
                valid_ids.add(int(numeric_id))

        except (TypeError, ValueError, OverflowError):
            continue

    if not valid_ids:
        return {}

    poster_data = {}

    # Gửi nhiều yêu cầu API đồng thời.
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_id = {
            executor.submit(
                fetch_tmdb_movie,
                tmdb_id,
                api_key,
            ): tmdb_id
            for tmdb_id in valid_ids
        }

        # Thu thập kết quả khi từng yêu cầu hoàn thành.
        for future in as_completed(future_to_id):
            tmdb_id = future_to_id[future]

            try:
                poster_data[tmdb_id] = future.result()
            except Exception:
                poster_data[tmdb_id] = {}

    return poster_data

# LẤY MÔ TẢ TIẾNG VIỆT
def get_vietnamese_overview(tmdb_id):
    info = fetch_tmdb_movie(
        tmdb_id,
        language="vi-VN",
    )

    overview = info.get("overview", "")

    # Nếu TMDB không có mô tả tiếng Việt,
    # thử lấy mô tả tiếng Anh.
    if not overview:
        english_info = fetch_tmdb_movie(
            tmdb_id,
            language="en-US",
        )

        overview = english_info.get("overview", "")

    return overview
