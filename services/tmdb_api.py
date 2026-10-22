from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import pandas as pd
import requests
import streamlit as st

# ==================================================
# 1. LẤY TMDB API KEY
# ==================================================

def get_tmdb_api_key():
    """Lấy API key từ biến môi trường hoặc secrets.toml."""

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

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_tmdb_movie(tmdb_id, api_key):
    """
    Gọi TMDB API để lấy thông tin một bộ phim.

    Cache kết quả trong 24 giờ.
    """

    if not api_key:
        return {}
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    try:
        response = requests.get(
            url,
            params={
                "api_key": api_key,
                "language": "vi-VN",
            },
            timeout=8,
        )

        response.raise_for_status()

        movie_info = response.json()

        # Lấy đường dẫn poster.
        poster_path = movie_info.get("poster_path")

        poster_url = (
            "https://image.tmdb.org/t/p/w342" + poster_path
            if poster_path
            else None
        )

        # Trả về các thông tin cần thiết cho giao diện.
        return {
            "poster_url": poster_url,
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

    except (requests.RequestException, ValueError):
        # Không làm ứng dụng bị dừng nếu API gặp lỗi.
        return {}


# ==================================================
# 3. LẤY THÔNG TIN NHIỀU PHIM
# ==================================================

def fetch_all_posters(tmdb_ids, api_key):
    """
    Lấy thông tin TMDB của nhiều phim.

    Các yêu cầu được thực hiện song song.
    Kết quả trả về là dictionary có tmdbId làm khóa.
    """

    if not api_key:
        return {}

    # Lọc ID trống, ID không hợp lệ và ID trùng nhau.
    valid_ids = set()

    for value in tmdb_ids:
        try:
            if pd.notna(value) and float(value) > 0:
                valid_ids.add(int(value))
        except (TypeError, ValueError):
            continue

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