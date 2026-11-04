import logging
import base64
import html

from urllib.parse import urlencode
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st

from PIL import Image, ImageDraw, ImageFont

from src.tmdb import (
    fetch_tmdb_poster,
    fetch_tmdb_movie,
    get_tmdb_api_key,
)


# ==================================================
# 1. CẤU HÌNH
# ==================================================

logger = logging.getLogger(__name__)

# Cache ảnh poster trong 24 giờ
POSTER_CACHE_TTL = 86400

# Số yêu cầu TMDb chạy đồng thời
MAX_WORKERS = 5

# Kích thước ảnh poster
POSTER_MAX_SIZE = (342, 513)


# ==================================================
# 2. KIỂM TRA TMDB ID
# ==================================================

def normalize_tmdb_id(value):
    """
    Chuyển TMDb ID về số nguyên hợp lệ.

    Trả về None nếu ID không hợp lệ.
    """

    try:
        if pd.isna(value):
            return None

        numeric_id = float(value)

        if (
            numeric_id <= 0
            or not numeric_id.is_integer()
        ):
            return None

        return int(numeric_id)

    except (
        ValueError,
        TypeError,
        OverflowError,
    ):
        return None


# ==================================================
# 3. LẤY POSTER CỦA MỘT PHIM
# ==================================================

def _fetch_one_poster(tmdb_id, api_key):
    """
    Lấy thông tin poster từ TMDb.

    Cách 1:
        Sử dụng API tải poster nhanh.

    Cách 2:
        Nếu không có poster, thử API chi tiết phim.

    Không tạo thêm cache tại đây vì các hàm
    trong src/tmdb.py đã có cache riêng.
    """

    tmdb_id = normalize_tmdb_id(tmdb_id)

    if tmdb_id is None or not api_key:
        return {}

    # ------------------------------------------
    # CÁCH 1: LẤY POSTER NHANH
    # ------------------------------------------

    try:
        info = fetch_tmdb_poster(
            tmdb_id,
            api_key,
        ) or {}

        if (
            info.get("poster_url")
            or info.get("poster")
        ):
            return info

    except Exception as error:
        logger.warning(
            "Lỗi tải poster nhanh phim %s: %s",
            tmdb_id,
            error,
        )

    # ------------------------------------------
    # CÁCH 2: LẤY TỪ THÔNG TIN CHI TIẾT
    # ------------------------------------------

    try:
        info = fetch_tmdb_movie(
            tmdb_id,
            api_key,
            language="en-US",
        ) or {}

        if (
            info.get("poster_url")
            or info.get("poster")
        ):
            return info

    except Exception as error:
        logger.warning(
            "Lỗi tải poster dự phòng phim %s: %s",
            tmdb_id,
            error,
        )

    return {}


# ==================================================
# 4. TẢI POSTER CHO DANH SÁCH PHIM
# ==================================================

def load_poster_data(
    movies,
    *,
    spinner_text=None,
    warn_if_missing_key=False,
):
    """
    Lấy thông tin poster của nhiều phim.

    Tham số:
        movies:
            DataFrame chứa cột tmdbId.

        spinner_text:
            Nội dung thông báo khi đang tải.

        warn_if_missing_key:
            Hiển thị cảnh báo nếu thiếu API key.
    """

    # ------------------------------------------
    # KIỂM TRA DỮ LIỆU
    # ------------------------------------------

    if movies is None:
        return {}

    if movies.empty:
        return {}

    if "tmdbId" not in movies.columns:
        logger.warning(
            "Dữ liệu phim không có cột tmdbId."
        )
        return {}

    # ------------------------------------------
    # LẤY API KEY
    # ------------------------------------------

    api_key = get_tmdb_api_key()

    if not api_key:

        if warn_if_missing_key:
            st.warning(
                "Chưa cấu hình TMDB_API_KEY. "
                "Không thể tải poster từ TMDb."
            )

        return {}

    # ------------------------------------------
    # LẤY DANH SÁCH TMDB ID
    # ------------------------------------------

    valid_ids = set()

    for value in movies["tmdbId"]:

        tmdb_id = normalize_tmdb_id(value)

        if tmdb_id is not None:
            valid_ids.add(tmdb_id)

    if not valid_ids:
        return {}

    # ------------------------------------------
    # TẢI POSTER SONG SONG
    # ------------------------------------------

    poster_data = {}

    def fetch_posters():

        with ThreadPoolExecutor(
            max_workers=MAX_WORKERS
        ) as executor:

            futures = {
                executor.submit(
                    _fetch_one_poster,
                    tmdb_id,
                    api_key,
                ): tmdb_id
                for tmdb_id in valid_ids
            }

            for future in as_completed(futures):

                tmdb_id = futures[future]

                try:
                    info = future.result()

                    if not isinstance(info, dict):
                        continue

                    poster_url = (
                        info.get("poster_url")
                        or info.get("poster")
                    )

                    # Chỉ lưu phim có URL poster
                    if poster_url:
                        poster_data[tmdb_id] = info

                except Exception as error:

                    logger.warning(
                        "Không thể tải poster phim %s: %s",
                        tmdb_id,
                        error,
                    )

    # ------------------------------------------
    # HIỂN THỊ SPINNER NẾU CẦN
    # ------------------------------------------

    if spinner_text:

        with st.spinner(spinner_text):
            fetch_posters()

    else:
        fetch_posters()

    return poster_data


# ==================================================
# 5. LẤY URL POSTER TỪ DỮ LIỆU
# ==================================================

def get_movie_poster_url(movie, poster_data):
    """
    Lấy URL poster của một phim.

    Dùng chung cho:
        - Trang chủ
        - Trang tìm kiếm
        - Trang gợi ý phim
        - Trang phim yêu thích
    """

    if movie is None:
        return None

    if not isinstance(poster_data, dict):
        return None

    tmdb_id = normalize_tmdb_id(
        movie.get("tmdbId")
    )

    if tmdb_id is None:
        return None

    info = poster_data.get(
        tmdb_id,
        {},
    ) or {}

    if not isinstance(info, dict):
        return None

    return (
        info.get("poster_url")
        or info.get("poster")
    )


# ==================================================
# 6. TẢI ẢNH POSTER VÀ LƯU CACHE
# ==================================================

@st.cache_data(
    ttl=POSTER_CACHE_TTL,
    show_spinner=False,
    max_entries=500,
)
def download_poster(url):
    """
    Tải ảnh poster từ URL.

    Ảnh tải thành công được lưu cache 24 giờ.

    Nếu tải thất bại, hàm phát sinh lỗi để
    bên ngoài xử lý và hiển thị ảnh mặc định.
    """

    if not url:
        raise ValueError(
            "URL poster không hợp lệ."
        )

    response = requests.get(
        url,
        timeout=(4, 10),
        headers={
            "User-Agent": "MovieMatch/1.0",
        },
    )

    response.raise_for_status()

    image = Image.open(
        BytesIO(response.content)
    )

    image = image.convert("RGB")

    # Giảm kích thước để tiết kiệm RAM
    image.thumbnail(
        POSTER_MAX_SIZE,
        Image.Resampling.LANCZOS,
    )

    return image


# ==================================================
# 7. TẠO POSTER MẶC ĐỊNH
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
# 8. LẤY ẢNH POSTER DÙNG CHUNG
# ==================================================

def _get_movie_poster_image(movie, poster_data):
    """
    Lấy ảnh poster của phim.

    Sử dụng chung cho:
        - show_movie_poster()
        - show_clickable_poster()

    Ưu tiên:
        1. Poster thật từ TMDb.
        2. Ảnh mặc định nếu không có poster.
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
# 9. HIỂN THỊ POSTER PHIM
# ==================================================

def show_movie_poster(
    movie,
    poster_data,
    width=150,
    *,
    clickable=False,
    return_page="home",
):
    """
    Hiển thị poster phim.

    Parameters:
        movie:
            Thông tin phim.

        poster_data:
            Dữ liệu poster từ TMDb.

        width:
            Chiều rộng poster.

        clickable:
            True: Poster có thể nhấn để mở chi tiết phim.
            False: Chỉ hiển thị poster.

        return_page:
            Trang quay lại sau khi xem chi tiết.

    Cả hai chế độ đều sử dụng chung cache ảnh.
    """

    # ------------------------------------------
    # 1. LẤY ẢNH POSTER
    # ------------------------------------------

    image = _get_movie_poster_image(
        movie,
        poster_data,
    )

    # ------------------------------------------
    # 2. XÁC ĐỊNH CHIỀU RỘNG
    # ------------------------------------------

    image_width = (
        "stretch"
        if width is None or width == "content"
        else width
    )

    # ------------------------------------------
    # 3. CHẾ ĐỘ HIỂN THỊ THÔNG THƯỜNG
    # ------------------------------------------

    if not clickable:

        st.image(
            image,
            width=image_width,
        )

        return

    # ------------------------------------------
    # 4. CHẾ ĐỘ POSTER CÓ THỂ NHẤN
    # ------------------------------------------

    movie_id = movie.get("movieId")

    if pd.isna(movie_id):
        movie_id = movie.get("movie_id")

    try:
        numeric_id = float(movie_id)

        if (
            numeric_id <= 0
            or not numeric_id.is_integer()
        ):
            raise ValueError("Movie ID không hợp lệ.")

        movie_id = int(numeric_id)

    except (TypeError, ValueError, OverflowError):

        # Không có ID hợp lệ thì chỉ hiển thị poster
        st.image(
            image,
            width=image_width,
        )

        return

    # ------------------------------------------
    # 5. CHUYỂN ẢNH CACHE SANG BASE64
    # ------------------------------------------

    image_buffer = BytesIO()

    image.save(
        image_buffer,
        format="JPEG",
        quality=90,
        optimize=True,
    )

    image_base64 = base64.b64encode(
        image_buffer.getvalue()
    ).decode("ascii")

    # ------------------------------------------
    # 6. TẠO ĐƯỜNG DẪN CHI TIẾT PHIM
    # ------------------------------------------

    title = html.escape(
        str(movie.get("title", "phim")),
        quote=True,
    )

    query_string = urlencode({
        "movie_id": movie_id,
        "return_page": return_page,
    })

    # ------------------------------------------
    # 7. XÁC ĐỊNH WIDTH HTML
    # ------------------------------------------

    if isinstance(width, (int, float)) and not isinstance(width, bool):
        width_style = f"width:{int(width)}px;"
    else:
        width_style = "width:100%;"

    # ------------------------------------------
    # 8. HIỂN THỊ POSTER DƯỚI DẠNG LIÊN KẾT
    # ------------------------------------------

    st.html(
        f"""
        <a
            class="home-movie-poster"
            href="?{query_string}"
            target="_self"
            title="Xem chi tiết {title}"
            style="
                display:block;
                {width_style}
                max-width:100%;
            "
        >
            <img
                src="data:image/jpeg;base64,{image_base64}"
                alt="{title}"
                loading="lazy"
                decoding="async"
                style="
                    display:block;
                    width:100%;
                    height:auto;
                    object-fit:cover;
                "
            >
        </a>
        """
    )


# ==================================================
# 10. HIỂN THỊ POSTER CÓ THỂ NHẤN
# ==================================================

def show_clickable_poster(movie, poster_data):
    """
    Hiển thị poster có thể nhấn để mở trang chi tiết.

    Kế thừa toàn bộ logic hiển thị và cache từ
    show_movie_poster().
    """

    return show_movie_poster(
        movie=movie,
        poster_data=poster_data,
        width=150,
        clickable=True,
        return_page="home",
    )

