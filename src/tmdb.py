import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st


# ==================================================
# 1. CẤU HÌNH TMDB
# ==================================================

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p"

logger = logging.getLogger(__name__)

MAX_WORKERS = 4

CACHE_TTL = 86400

# Cache poster thành công trong bộ nhớ
_POSTER_CACHE = {}


# ==================================================
# 2. LẤY API KEY
# ==================================================

def get_tmdb_api_key():

    api_key = os.getenv(
        "TMDB_API_KEY", ""
    ).strip()

    if api_key:
        return api_key

    try:
        return str(
            st.secrets.get(
                "TMDB_API_KEY", ""
            )
        ).strip()

    except Exception:
        return ""


# ==================================================
# 3. CHUẨN HÓA TMDB ID
# ==================================================

def normalize_tmdb_id(value):

    try:
        if pd.isna(value):
            return None

        number = float(value)

        if number <= 0 or not number.is_integer():
            return None

        return int(number)

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None


# ==================================================
# 4. GỌI TMDB API
# ==================================================

def _request_tmdb(
    endpoint,
    api_key,
    language="vi-VN",
    timeout=8,
    retries=2,
):

    if not api_key:
        return {}

    url = f"{TMDB_BASE_URL}{endpoint}"

    for attempt in range(retries + 1):

        try:

            response = requests.get(
                url,
                params={
                    "api_key": api_key,
                    "language": language,
                },
                timeout=(3, timeout),
            )

            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict):
                return data

            return {}

        except requests.RequestException as error:

            logger.warning(
                "TMDb lỗi %s - lần %s/%s: %s",
                endpoint,
                attempt + 1,
                retries + 1,
                error,
            )

            if attempt < retries:
                time.sleep(
                    0.5 * (attempt + 1)
                )

        except ValueError:
            return {}

    return {}


# ==================================================
# 5. LẤY POSTER MỘT PHIM
# ==================================================

def fetch_tmdb_poster(tmdb_id, api_key):
    """
    Lấy poster theo TMDb ID.

    Chỉ cache kết quả thành công.
    """

    tmdb_id = normalize_tmdb_id(tmdb_id)

    if tmdb_id is None or not api_key:
        return {}

    cache_key = (
        tmdb_id,
        api_key,
    )

    current_time = time.time()

    # Kiểm tra cache
    cached = _POSTER_CACHE.get(cache_key)

    if cached:

        timestamp, info = cached

        if current_time - timestamp < CACHE_TTL:
            return info.copy()

    # Lấy dữ liệu TMDb
    data = _request_tmdb(
        f"/movie/{tmdb_id}",
        api_key,
        language="en-US",
        timeout=8,
        retries=2,
    )

    if not data:
        return {}

    poster_path = data.get("poster_path")

    if not poster_path:
        return {}

    info = {
        "poster_url": (
            f"{TMDB_IMAGE_URL}/w342{poster_path}"
        ),
        "poster": (
            f"{TMDB_IMAGE_URL}/w500{poster_path}"
        ),
    }

    # Chỉ cache khi có poster
    _POSTER_CACHE[cache_key] = (
        current_time,
        info,
    )

    return info.copy()


# ==================================================
# 6. LẤY THÔNG TIN CHI TIẾT PHIM
# ==================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def fetch_tmdb_movie(
    tmdb_id,
    api_key,
    language="vi-VN",
):

    tmdb_id = normalize_tmdb_id(tmdb_id)

    if tmdb_id is None or not api_key:
        return {}

    data = _request_tmdb(
        f"/movie/{tmdb_id}",
        api_key,
        language=language,
        timeout=8,
        retries=1,
    )

    if not data:
        return {}

    # Bổ sung poster và backdrop nếu thiếu
    if language == "vi-VN" and (
        not data.get("poster_path")
        or not data.get("backdrop_path")
    ):

        english = _request_tmdb(
            f"/movie/{tmdb_id}",
            api_key,
            language="en-US",
            timeout=8,
            retries=1,
        )

        if english:

            for field in (
                "poster_path",
                "backdrop_path",
            ):

                if not data.get(field):
                    data[field] = english.get(field)

    poster_path = data.get("poster_path")
    backdrop_path = data.get("backdrop_path")

    return {
        "poster_url": (
            f"{TMDB_IMAGE_URL}/w342{poster_path}"
            if poster_path else None
        ),

        "poster": (
            f"{TMDB_IMAGE_URL}/w500{poster_path}"
            if poster_path else None
        ),

        "backdrop": (
            f"{TMDB_IMAGE_URL}/w1280{backdrop_path}"
            if backdrop_path else None
        ),

        "tmdb_title": data.get(
            "title", ""
        ),

        "overview": data.get(
            "overview", ""
        ),

        "release_date": data.get(
            "release_date", ""
        ),

        "runtime": data.get(
            "runtime"
        ),

        "tmdb_vote_average": data.get(
            "vote_average"
        ),

        "original_language": data.get(
            "original_language", ""
        ),

        "tagline": data.get(
            "tagline", ""
        ),

        "tmdb_genres": [
            genre.get("name", "")
            for genre in data.get(
                "genres", []
            )
        ],

        "homepage": data.get(
            "homepage", ""
        ),
    }


# ==================================================
# 7. LẤY POSTER NHIỀU PHIM
# ==================================================

def fetch_all_posters(
    tmdb_ids,
    api_key,
):

    if not api_key or tmdb_ids is None:
        return {}

    valid_ids = set()

    for value in tmdb_ids:

        tmdb_id = normalize_tmdb_id(value)

        if tmdb_id is not None:
            valid_ids.add(tmdb_id)

    if not valid_ids:
        return {}

    poster_data = {}

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {
            executor.submit(
                fetch_tmdb_poster,
                tmdb_id,
                api_key,
            ): tmdb_id
            for tmdb_id in valid_ids
        }

        for future in as_completed(futures):

            tmdb_id = futures[future]

            try:

                info = future.result()

                if info:
                    poster_data[tmdb_id] = info

            except Exception as error:

                logger.warning(
                    "Lỗi tải poster %s: %s",
                    tmdb_id,
                    error,
                )

    return poster_data


# ==================================================
# 8. LẤY MÔ TẢ TIẾNG VIỆT
# ==================================================

def get_vietnamese_overview(
    tmdb_id,
    api_key=None,
):

    if api_key is None:
        api_key = get_tmdb_api_key()

    if not api_key:
        return ""

    info = fetch_tmdb_movie(
        tmdb_id,
        api_key,
        language="vi-VN",
    )

    overview = info.get(
        "overview", ""
    )

    if overview:
        return overview

    english_info = fetch_tmdb_movie(
        tmdb_id,
        api_key,
        language="en-US",
    )

    return english_info.get(
        "overview", ""
    )


# ==================================================
# 9. LẤY TRAILER
# ==================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def fetch_movie_trailer(
    tmdb_id,
    api_key,
):

    tmdb_id = normalize_tmdb_id(tmdb_id)

    if tmdb_id is None or not api_key:
        return None

    for language in (
        "vi-VN",
        "en-US",
    ):

        data = _request_tmdb(
            f"/movie/{tmdb_id}/videos",
            api_key,
            language=language,
            timeout=8,
            retries=1,
        )

        videos = data.get(
            "results", []
        )

        youtube_videos = [
            video
            for video in videos
            if (
                video.get("site") == "YouTube"
                and video.get("key")
                and video.get("type")
                in ("Trailer", "Teaser")
            )
        ]

        youtube_videos.sort(
            key=lambda video: (
                video.get("type") != "Trailer",
                not video.get(
                    "official", False
                ),
            )
        )

        if youtube_videos:

            video_key = (
                youtube_videos[0]["key"]
            )

            return (
                "https://www.youtube.com/watch?v="
                f"{video_key}"
            )

    return None