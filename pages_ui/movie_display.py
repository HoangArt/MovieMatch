import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from src.tmdb import fetch_all_posters, get_tmdb_api_key

# Cache kết quả lấy poster trong 24 giờ để hạn chế gọi TMDB lại khi Streamlit chạy lại


@st.cache_data(ttl=24*60*60, max_entries=128, show_spinner=False)
def _fetch_posters_cached(tmdb_ids: tuple[int, ...], api_key: str):
    return fetch_all_posters(list(tmdb_ids), api_key)


def load_poster_data(movies, *, spinner_text="Đang tải poster phim từ TMDB...", warn_if_missing_key=False):
    """
    Tải poster cho một DataFrame phim và trả về dictionary theo tmdbId.
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

    # Lọc ID rỗng/ không hợp lệ và giữ thứ tự, đồng thời loại ID trùng
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

    # Chuyển thành tuple để dùng làm khóa cache.
    ids_key = tuple(tmdb_ids)

    if spinner_text:
        with st.spinner(spinner_text):
            return _fetch_posters_cached(ids_key, api_key)

    return fetch_all_posters(ids_key, api_key)



@st.cache_resource
def _create_placeholder_poster():
    """
    Tạo poster đối với phim không có sẵn poster
    """
    image = Image.new("RGB", (600, 900), (32, 32, 39))
    
    draw = ImageDraw.Draw(image)
    
    # Viền poster.
    draw.rounded_rectangle((16, 16, 584, 884), radius=24, outline=(75, 75, 90), width=4)
    
    # Biểu tượng phim ở giữa.
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



def show_movie_poster(movie, poster_data, width=150):
    """Hiển thị poster phim với kích thước đồng nhất"""
    tmdb_id = movie.get("tmdbId")
    poster_url = None

    try:
        if pd.notna(tmdb_id):
            tmdb_id = int(float(tmdb_id))
            movie_info = (poster_data or {}).get(tmdb_id, {}) or {}
            poster_url = movie_info.get("poster_url")

    except (TypeError, ValueError, OverflowError):
        poster_url = None

    # width=None nghĩa là poster chiếm toàn bộ chiều rộng cột.
    # width là số nguyên nghĩa là dùng chiều rộng cố định.
    image_width = "stretch" if width is None else width

    title = str(movie.get("title", "phim"))

    if poster_url:
        st.image(poster_url, width=image_width, alt=f"Poster phim {title}")
    else:
        st.image(_create_placeholder_poster(), width=image_width, alt=f"Không có poster cho phim {title}")
