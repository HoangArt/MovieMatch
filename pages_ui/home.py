import hashlib

import pandas as pd
import streamlit as st

from src.common import (
    load_movie_data,
    GENRE_TRANSLATIONS,
    shorten_text,
    format_movie_title,
)

from src.tmdb import get_tmdb_api_key

from pages_ui.movie_display import (
    load_poster_data,
    show_clickable_poster,
)

from assets.style import HOME_CSS


# ==================================================
# 1. CẤU HÌNH CACHE
# ==================================================

# Thời gian cache: 24 giờ
POSTER_CACHE_TTL = 86400


# ==================================================
# 2. LẤY DANH SÁCH TMDB ID
# ==================================================

def get_unique_tmdb_ids(movies):
    """
    Lấy danh sách TMDB ID hợp lệ và loại bỏ trùng lặp.

    Trả về tuple đã sắp xếp để tạo cache key ổn định.
    """

    if movies is None or movies.empty:
        return ()

    if "tmdbId" not in movies.columns:
        return ()

    tmdb_ids = set()

    for value in movies["tmdbId"]:

        try:
            if pd.isna(value):
                continue

            numeric_id = float(value)

            if numeric_id <= 0 or not numeric_id.is_integer():
                continue

            tmdb_ids.add(int(numeric_id))

        except (ValueError, TypeError, OverflowError):
            continue

    return tuple(sorted(tmdb_ids))


# ==================================================
# 3. CACHE THÔNG TIN POSTER TỪ TMDB
# ==================================================

@st.cache_data(
    ttl=POSTER_CACHE_TTL,
    max_entries=20,
    show_spinner=False,
)
def load_home_poster_cache(tmdb_ids, api_key_hash):
    """
    Cache thông tin poster của toàn bộ phim trên Home.

    Cache key bao gồm:
        - Danh sách TMDB ID.
        - Hash của TMDB API Key.

    Nhờ đó:
        - Rerun không phải tải lại dữ liệu.
        - Chuyển trang quay lại Home không gọi TMDB lại.
        - Thay API Key sẽ tạo cache mới.
    """

    if not tmdb_ids:
        return {}

    # Tạo DataFrame chỉ chứa TMDB ID
    poster_movies = pd.DataFrame({
        "tmdbId": list(tmdb_ids)
    })

    # Tải thông tin poster.
    # Chỉ chạy khi cache chưa có hoặc đã hết hạn.
    poster_data = load_poster_data(
        poster_movies,
        spinner_text="Đang tải poster phim từ TMDB...",
        warn_if_missing_key=False,
    )

    return poster_data


# ==================================================
# 4. TẠO CÁC DANH MỤC PHIM
# ==================================================

def create_movie_sections(movie_data):
    """
    Tạo các danh mục phim từ dữ liệu MovieLens.
    """

    sections = []

    # Danh mục 1: Phim được đánh giá nhiều
    popular_movies = movie_data.sort_values(
        by=["rating_count", "avg_rating"],
        ascending=[False, False],
        na_position="last",
    ).head(10)

    sections.append(("Phim phổ biến", popular_movies))

    # Danh mục 2: Phim được đánh giá cao
    highly_rated = movie_data[
        movie_data["rating_count"] >= 20
    ].sort_values(
        by=["avg_rating", "rating_count"],
        ascending=[False, False],
        na_position="last",
    ).head(10)

    sections.append(("Phim được đánh giá cao", highly_rated))

    # Danh mục 3: Phim phát hành gần đây
    recent_movies = movie_data[
        movie_data["year"].notna()
    ].sort_values(
        by=["year", "rating_count"],
        ascending=[False, False],
        na_position="last",
    ).head(10)

    sections.append(
        ("Phim phát hành gần đây trong dữ liệu", recent_movies)
    )

    # Danh mục theo thể loại
    genres = list(GENRE_TRANSLATIONS.items())

    for genre, section_title in genres:

        genre_movies = movie_data[
            movie_data["genres"].fillna("").apply(
                lambda value: genre in value.split("|")
            )
        ]

        genre_movies = genre_movies.sort_values(
            by=["rating_count", "avg_rating"],
            ascending=[False, False],
            na_position="last",
        ).head(10)

        sections.append((section_title, genre_movies))

    return sections


# ==================================================
# 5. HIỂN THỊ MỘT DANH MỤC PHIM
# ==================================================

def show_movie_section(section_title, movies, poster_data):
    """
    Hiển thị poster, tên phim, rating và nút xem chi tiết.
    """

    st.subheader(section_title)

    if movies.empty:
        st.write("Chưa có phim trong danh mục này.")
        return

    with st.container(horizontal=True, wrap=True, gap="small"):

        for _, movie in movies.iterrows():

            with st.container(width=170):

                # 1. Hiển thị poster từ cache
                show_clickable_poster(movie, poster_data)

                # 2. Tên phim
                st.write(
                    f"**{shorten_text(format_movie_title(movie['title']), max_chars=20)}**"
                )

                # 3. Điểm đánh giá
                avg_rating = movie["avg_rating"]

                if pd.notna(avg_rating):
                    st.caption(f"Đánh giá: {avg_rating:.1f}/5")
                else:
                    st.caption("Chưa có điểm đánh giá")

                # 4. Số lượt đánh giá
                rating_count = movie["rating_count"]

                st.caption(f"{rating_count:,} lượt đánh giá")

                # 5. ID phim
                movie_id = movie.get("movieId")

                if pd.isna(movie_id):
                    movie_id = movie.get("movie_id")

                # 6. Nút xem chi tiết
                if pd.notna(movie_id):

                    movie_id = int(movie_id)

                    if st.button("Xem chi tiết", key=f"detail_{section_title}_{movie_id}", width="stretch"):
                        st.query_params["movie_id"] = str(movie_id)
                        st.query_params["return_page"] = "Trang chủ"
                        st.rerun()


# ==================================================
# 6. HIỂN THỊ TRANG CHỦ
# ==================================================

def show_home_page():

    st.title("MovieMatch")

    st.write(
        "Khám phá phim dựa trên dữ liệu đánh giá "
        "của cộng đồng MovieLens."
    )

    st.html(HOME_CSS)

    # ----------------------------------------------
    # ĐỌC DỮ LIỆU PHIM
    # ----------------------------------------------

    try:
        movie_data = load_movie_data()

    except Exception as error:

        st.error("Không thể tải hoặc đọc dữ liệu MovieLens.")

        st.write(
            "Hãy kiểm tra kết nối Internet, cấu trúc "
            "thư mục dataset và các file CSV."
        )

        with st.expander("Chi tiết lỗi"):
            st.exception(error)

        return

    # ----------------------------------------------
    # TẠO DANH MỤC PHIM
    # ----------------------------------------------

    sections = create_movie_sections(movie_data)

    # ----------------------------------------------
    # GỘP TẤT CẢ PHIM CẦN HIỂN THỊ
    # ----------------------------------------------

    section_movie_frames = [
        section_movies
        for _, section_movies in sections
        if not section_movies.empty
    ]

    if section_movie_frames:

        movies_to_display = pd.concat(
            section_movie_frames,
            ignore_index=True,
        )

        # Loại phim trùng theo MovieLens ID
        if "movieId" in movies_to_display.columns:

            movies_to_display = movies_to_display.drop_duplicates(
                subset=["movieId"]
            )

        # Đồng thời loại trùng theo TMDB ID
        if "tmdbId" in movies_to_display.columns:

            movies_to_display = movies_to_display.drop_duplicates(
                subset=["tmdbId"],
                keep="first",
            )

    else:

        movies_to_display = movie_data.iloc[0:0].copy()

    # ----------------------------------------------
    # LẤY DANH SÁCH TMDB ID
    # ----------------------------------------------

    tmdb_ids = get_unique_tmdb_ids(
        movies_to_display
    )

    # ----------------------------------------------
    # TẢI POSTER TỪ CACHE
    # ----------------------------------------------

    poster_data = {}

    if not tmdb_ids:

        st.info("Không có TMDB ID hợp lệ để tải poster.")

    else:

        api_key = get_tmdb_api_key()

        if not api_key:

            st.warning(
                "Chưa cấu hình TMDB_API_KEY. "
                "Không thể tải poster từ TMDB."
            )

        else:

            # Không lưu API Key trực tiếp vào cache key.
            # Chỉ sử dụng SHA256 để nhận diện API Key.
            api_key_hash = hashlib.sha256(
                api_key.encode("utf-8")
            ).hexdigest()

            # Lần đầu: gọi TMDB và lưu cache.
            # Những lần sau: lấy dữ liệu từ cache.
            poster_data = load_home_poster_cache(
                tmdb_ids,
                api_key_hash,
            )

    # ----------------------------------------------
    # HIỂN THỊ CÁC DANH MỤC PHIM
    # ----------------------------------------------

    for section_title, section_movies in sections:

        show_movie_section(
            section_title,
            section_movies,
            poster_data,
        )
