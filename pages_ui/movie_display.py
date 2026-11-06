import logging
import math
import pandas as pd
import requests
import streamlit as st

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont, ImageOps
from src.tmdb import fetch_tmdb_poster, fetch_tmdb_movie, get_tmdb_api_key


# ==================================================
# 1. CẤU HÌNH
# ==================================================

logger = logging.getLogger(__name__)

# Cache
POSTER_CACHE_TTL = 24 * 60 * 60

# Số luồng tải TMDb đồng thời
MAX_WORKERS = 5

# Kích thước poster
POSTER_MAX_SIZE = (342, 513)

# Giới hạn tải ảnh
MAX_POSTER_BYTES = 8 * 1024 * 1024
MAX_POSTER_PIXELS = 40_000_000


# ==================================================
# 2. ĐIỀU HƯỚNG CHI TIẾT PHIM
# ==================================================

RETURN_PAGE_ALIASES = {
    "home": "home",
    "trang chủ": "home",

    "search": "search",
    "tìm kiếm": "search",

    "recommendations": "recommendations",
    "gợi ý phim": "recommendations",

    "favorite_movies": "favorite_movies",
    "favorites": "favorite_movies",
    "phim yêu thích": "favorite_movies",

    "rated_movies": "rated_movies",
    "phim đã đánh giá": "rated_movies",

    "stats": "stats",
    "thống kê": "stats",
}


def normalize_return_page(return_page="home"):
    """Chuẩn hóa trang quay lại."""

    value = str(return_page or "home").strip().casefold()

    return RETURN_PAGE_ALIASES.get(value, "home")


def normalize_movie_id(movie_id):
    """Chuyển MovieLens ID thành số nguyên dương."""

    if movie_id is None or isinstance(movie_id, bool):
        raise ValueError("Movie ID không hợp lệ.")

    try:
        numeric_id = float(movie_id)

    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Movie ID không hợp lệ.") from error

    if (
        not math.isfinite(numeric_id)
        or numeric_id <= 0
        or not numeric_id.is_integer()
    ):
        raise ValueError("Movie ID không hợp lệ.")

    return int(numeric_id)


def navigate_to_movie_detail(movie_id, return_page="home"):
    """
    Mở trang chi tiết phim.

    Giữ nguyên các query parameters khác
    và không sử dụng HTML anchor.
    """

    try:
        movie_id = normalize_movie_id(movie_id)

    except ValueError:
        logger.warning(
            "Movie ID không hợp lệ: %r",
            movie_id,
        )

        st.error("Movie ID không hợp lệ.")
        return

    return_page = normalize_return_page(return_page)

    st.query_params["movie_id"] = str(movie_id)
    st.query_params["return_page"] = return_page

    st.rerun()



# ==================================================
# 4. KIỂM TRA TMDB ID
# ==================================================

def normalize_tmdb_id(value):
    """Chuẩn hóa TMDb ID; trả None nếu không hợp lệ."""

    try:
        return normalize_movie_id(value)

    except ValueError:
        return None


# ==================================================
# 5. LẤY POSTER TỪ TMDB
# ==================================================

def _get_poster_url_from_info(info):

    if not isinstance(info, dict):
        return None

    url = info.get("poster_url") or info.get("poster")

    if isinstance(url, str) and url.strip():
        return url.strip()

    return None


def _fetch_one_poster(tmdb_id, api_key):
    """
    Lấy poster theo hai bước:

    1. API poster nhanh.
    2. API chi tiết phim nếu cần.
    """

    tmdb_id = normalize_tmdb_id(tmdb_id)

    if tmdb_id is None or not api_key:
        return {}

    # Bước 1: API poster nhanh
    try:

        info = fetch_tmdb_poster(
            tmdb_id,
            api_key,
        ) or {}

        if _get_poster_url_from_info(info):
            return info

    except Exception as error:

        logger.warning(
            "Lỗi tải poster nhanh phim %s: %s",
            tmdb_id,
            error,
        )

    # Bước 2: API chi tiết phim
    try:

        info = fetch_tmdb_movie(
            tmdb_id,
            api_key,
            language="en-US",
        ) or {}

        if _get_poster_url_from_info(info):
            return info

    except Exception as error:

        logger.warning(
            "Lỗi tải poster dự phòng phim %s: %s",
            tmdb_id,
            error,
        )

    return {}


# ==================================================
# 6. TẢI POSTER CHO DANH SÁCH PHIM
# ==================================================

def load_poster_data(
    movies,
    *,
    spinner_text=None,
    warn_if_missing_key=False,
):
    """
    Tải thông tin poster cho danh sách phim.

    - Loại bỏ TMDb ID không hợp lệ.
    - Loại bỏ ID trùng lặp.
    - Tải song song.
    - Giới hạn số luồng.
    """

    if not isinstance(movies, pd.DataFrame):
        return {}

    if movies.empty:
        return {}

    if "tmdbId" not in movies.columns:

        logger.warning(
            "Dữ liệu phim không có cột tmdbId."
        )

        return {}

    api_key = get_tmdb_api_key()

    if not api_key:

        if warn_if_missing_key:
            st.warning(
                "Chưa cấu hình TMDB_API_KEY. "
                "Không thể tải poster từ TMDb."
            )

        return {}

    # Lọc và sắp xếp ID duy nhất
    tmdb_ids = sorted({
        tmdb_id
        for value in movies["tmdbId"]
        if (
            tmdb_id := normalize_tmdb_id(value)
        ) is not None
    })

    if not tmdb_ids:
        return {}

    def _load():

        poster_data = {}

        worker_count = min(
            MAX_WORKERS,
            len(tmdb_ids),
        )

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as executor:

            futures = {
                executor.submit(
                    _fetch_one_poster,
                    tmdb_id,
                    api_key,
                ): tmdb_id
                for tmdb_id in tmdb_ids
            }

            for future in as_completed(futures):

                tmdb_id = futures[future]

                try:
                    info = future.result()

                except Exception:

                    logger.exception(
                        "Không thể tải poster phim %s",
                        tmdb_id,
                    )

                    continue

                if _get_poster_url_from_info(info):
                    poster_data[tmdb_id] = info

        return poster_data

    if spinner_text:

        with st.spinner(spinner_text):
            return _load()

    return _load()


# ==================================================
# 7. LẤY URL POSTER TỪ DỮ LIỆU
# ==================================================

def get_movie_poster_url(movie, poster_data):
    """Lấy URL poster từ TMDb ID."""

    if movie is None or not isinstance(poster_data, dict):
        return None

    tmdb_id = normalize_tmdb_id(
        movie.get("tmdbId")
    )

    if tmdb_id is None:
        return None

    return _get_poster_url_from_info(
        poster_data.get(tmdb_id)
    )


# ==================================================
# 8. TẢI ẢNH POSTER VÀ LƯU CACHE
# ==================================================

@st.cache_data(
    ttl=POSTER_CACHE_TTL,
    show_spinner=False,
    max_entries=500,
)
def download_poster(url):
    """
    Tải poster, kiểm tra dung lượng và thu nhỏ ảnh.
    """

    if (
        not isinstance(url, str)
        or not url.startswith(("https://", "http://"))
    ):
        raise ValueError("URL poster không hợp lệ.")

    chunks = []
    total_bytes = 0

    with requests.get(
        url,
        timeout=(4, 10),
        headers={
            "User-Agent": "MovieMatch/1.0",
        },
        stream=True,
    ) as response:

        response.raise_for_status()

        content_length = response.headers.get("Content-Length")

        try:
            declared_size = (
                int(content_length)
                if content_length
                else None
            )
        except (TypeError, ValueError):
            declared_size = None

        if (
            declared_size is not None
            and declared_size > MAX_POSTER_BYTES
        ):
            raise ValueError(
                "Ảnh poster vượt quá giới hạn dung lượng."
            )

        for chunk in response.iter_content(
            chunk_size=64 * 1024
        ):

            if not chunk:
                continue

            total_bytes += len(chunk)

            if total_bytes > MAX_POSTER_BYTES:
                raise ValueError(
                    "Ảnh poster vượt quá giới hạn dung lượng."
                )

            chunks.append(chunk)

    image_bytes = b"".join(chunks)

    with Image.open(BytesIO(image_bytes)) as source:

        if source.width * source.height > MAX_POSTER_PIXELS:
            raise ValueError(
                "Kích thước ảnh poster vượt quá giới hạn."
            )

        image = ImageOps.exif_transpose(
            source
        ).convert("RGB")

    image.thumbnail(
        POSTER_MAX_SIZE,
        Image.Resampling.LANCZOS,
    )

    return image


# ==================================================
# 9. CHUYỂN ẢNH SANG DATA URI
# ==================================================

@st.cache_resource
def create_placeholder():
    """
    Tạo ảnh mặc định khi:
        - Phim không có poster
        - TMDb bị lỗi
        - URL poster không tải được
    """

    width = 600
    height = 900

    image = Image.new("RGB", (width, height), (32, 32, 39))

    draw = ImageDraw.Draw(image)

    # Khung poster
    draw.rounded_rectangle((220, 280, 380, 440), radius=16, outline=(150, 150, 170), width=8)
    draw.rectangle((245, 305, 355, 415), outline=(150, 150, 170), width=5)

    title_font = ImageFont.load_default(size=58)
    subtitle_font = ImageFont.load_default(size=28)

    def draw_centered_text(text, y, font, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
    
        draw.text(((600 - text_width) / 2, y), text, font=font, fill=fill)
    
    # Chữ chính
    draw_centered_text("NO POSTER", 510, title_font, (230, 230, 240))
    
    # Chữ phụ
    draw_centered_text("Image unavailable", 590, subtitle_font, (165, 165, 180))

    return image

# ==================================================
# 11. LẤY ẢNH POSTER DÙNG CHUNG
# ==================================================

def _get_movie_poster_image(movie, poster_data):
    """
    Lấy ảnh poster của phim.

    """

    poster_url = get_movie_poster_url(
        movie,
        poster_data,
    )

    if poster_url:
        try:
            # Sử dụng ảnh đã cache trong download_poster()
            return download_poster(poster_url)

        except Exception as error:
            logger.warning(
                "Không thể tải poster %s: %s",
                poster_url,
                error,
            )

    # Sử dụng ảnh mặc định đã cache
    return create_placeholder()


# ==================================================
# 12. HIỂN THỊ POSTER PHIM
# ==================================================

def show_movie_poster(movie, poster_data, width=150, *, clickable=False, return_page="home", key=None):
    """Hiển thị poster tĩnh; nhấn vào ảnh không thực hiện điều hướng."""

    image_width = ("stretch" if width is None or width == "content" else width)
    alt_text = (str(movie.get("title", "Poster phim")) if movie is not None else "Poster phim")
    st.image(_get_movie_poster_image(movie, poster_data), width=image_width, alt=alt_text)