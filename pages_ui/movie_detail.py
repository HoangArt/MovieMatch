import html
import pandas as pd
import streamlit as st

from src.common import load_movie_data, format_movie_title, translate_genres
from src.tmdb import fetch_tmdb_movie, fetch_movie_trailer, get_tmdb_api_key, normalize_tmdb_id
from assets.style import MOVIE_DETAIL_CSS
from pages_ui.movie_display import show_movie_poster
from pages_ui.rating_widget import show_rating_widget

MAIN_PAGES = [
    "Trang chủ",
    "Tìm kiếm",
    "Gợi ý phim",
    "Phim yêu thích",
    "Phim đã đánh giá",
    "Thống kê",
]


def safe_html(value):
    """Chuyển nội dung về HTML an toàn."""

    if value is None:
        return ""

    return html.escape(str(value), quote=True)


def create_meta_item(label, value, highlight=False):
    """Tạo một thẻ thông tin phim."""

    if value is None or value == "":
        return ""

    value_html = safe_html(value)

    value_class = ("mm-rating-value" if highlight else "mm-meta-value")

    return f"""
        <div class="mm-meta-item">
            <div class="mm-meta-label">
                {safe_html(label)}
            </div>

            <div class="{value_class}">
                {value_html}
            </div>
        </div>
    """


def create_movie_info_html(movie, tmdb_info):
    """Tạo giao diện thông tin phim."""

    metadata = []

    # Năm phát hành
    year = movie.get("year")
    if pd.notna(year):
        metadata.append(create_meta_item("Năm phát hành", int(year)))


    # Thể loại
    genres = translate_genres(movie.get("genres", ""))
    if genres:
        metadata.append(create_meta_item("Thể loại", genres))


    # Điểm MovieLens
    avg_rating = movie.get("avg_rating")
    if pd.notna(avg_rating):
        metadata.append(create_meta_item("Điểm MovieLens", f"{float(avg_rating):.2f}/5", highlight=True))


    # Số lượt đánh giá
    rating_count = movie.get("rating_count", 0)
    if pd.notna(rating_count):
        metadata.append(create_meta_item("Lượt đánh giá", f"{int(rating_count):,}"))


    # Thời lượng
    runtime = tmdb_info.get("runtime")
    if runtime:
        metadata.append(create_meta_item("Thời lượng", f"{runtime} phút"))


    # Ngày phát hành
    release_date = tmdb_info.get("release_date")
    if release_date:
        metadata.append(create_meta_item("Ngày công chiếu", release_date))


    # Điểm TMDb
    tmdb_rating = tmdb_info.get("tmdb_vote_average")
    if tmdb_rating is not None:
        try:
            metadata.append(create_meta_item("Điểm TMDb", f"{float(tmdb_rating):.1f}/10", highlight=True))
        except (ValueError, TypeError):
            pass


    # Ngôn ngữ
    original_language = tmdb_info.get("original_language")
    if original_language:
        metadata.append(create_meta_item("Ngôn ngữ gốc", original_language.upper()))


    tagline = tmdb_info.get("tagline")


    tagline_html = ""
    if tagline:
        tagline_html = f"""
            <div class="mm-tagline">
                “{safe_html(tagline)}”
            </div>
        """

    return f"""
        <div class="mm-info-card">

            <div class="mm-info-heading">
                Thông tin phim
            </div>

            <div class="mm-meta-grid">
                {''.join(metadata)}
            </div>

            {tagline_html}

        </div>
    """




@st.cache_data(
    ttl=86400,
    max_entries=500,
    show_spinner=False,
)
def load_movie_tmdb_detail(tmdb_id, api_key):
    """
    Tải thông tin phim và trailer từ TMDb.

    Cache trong 24 giờ để tránh gọi API lại
    khi Streamlit rerun.
    """

    if not api_key or tmdb_id is None:
        return {}, None

    tmdb_info = {}

    # Thông tin tiếng Việt
    tmdb_info = fetch_tmdb_movie(
        tmdb_id,
        api_key,
        language="vi-VN",
    ) or {}

    # Dữ liệu tiếng Anh dự phòng
    if (
        not tmdb_info.get("overview")
        or not tmdb_info.get("poster_url")
    ):

        english_info = fetch_tmdb_movie(
            tmdb_id,
            api_key,
            language="en-US",
        ) or {}

        for field, value in english_info.items():

            if not tmdb_info.get(field):
                tmdb_info[field] = value

    trailer_url = fetch_movie_trailer(
        tmdb_id,
        api_key,
    )

    return tmdb_info, trailer_url


# ==================================================
# 4. HIỂN THỊ TIÊU ĐỀ KHU VỰC
# ==================================================

def show_section_heading(title):
    """Hiển thị tiêu đề khu vực."""

    st.html(
        f"""
        <div class="mm-section">
            <div class="mm-section-title">
                {safe_html(title)}
            </div>
        </div>
        """
    )


def get_return_page():
    """
    Lấy trang trước đó từ query_params.

    Hỗ trợ cả tên trang tiếng Việt và alias tiếng Anh.
    """

    return_page = st.query_params.get("return_page", "Trang chủ")

    # Chuẩn hóa tên trang
    return_page = str(return_page).strip()

    aliases = {
        "home": "Trang chủ",
        "search": "Tìm kiếm",
        "recommendations": "Gợi ý phim",
        "favorite_movies": "Phim yêu thích",
        "favorites": "Phim yêu thích",
        "rated_movies": "Phim đã đánh giá",
        "stats": "Thống kê",
    }

    return_page = aliases.get(
        return_page.lower(),
        return_page,
    )

    # Chỉ cho phép điều hướng đến những trang hợp lệ
    if return_page not in MAIN_PAGES:
        return_page = "Trang chủ"

    return return_page


def navigate_back():
    """
    Quay lại trang trước đó.

    1. Lấy return_page.
    2. Cập nhật trạng thái thanh điều hướng.
    3. Xóa query_params của trang chi tiết.
    4. Chạy lại ứng dụng.
    """

    return_page = get_return_page()

    # Cập nhật trang đang được chọn trong sidebar
    st.session_state["main_navigation"] = return_page

    # Xóa movie_id và return_page
    st.query_params.clear()

    # Điều hướng về trang trước
    st.rerun()


def show_movie_detail_page(movie_id):
    """
    Trang chi tiết phim MovieMatch
    Bao gồm:
        - Poster phim
        - Thông tin TMDb và MovieLens
        - Nội dung phim
        - Trailer
        - Khu vực đánh giá
    """

    st.html(MOVIE_DETAIL_CSS)


    # ĐỌC DỮ LIỆU PHIM
    try:
        movie_id = int(movie_id)
        movie_data = load_movie_data()
        movie_rows = movie_data[movie_data["movieId"] == movie_id]
    except (TypeError, ValueError, OverflowError) as error:
        st.error("ID phim không hợp lệ.")
        return

    if movie_rows.empty:
        st.error("Không tìm thấy bộ phim này.")
        if st.button("Quay lại", key="movie_not_found_back"):
            navigate_back()
        return

    movie = movie_rows.iloc[0]

    # NÚT QUAY LẠI
    if st.button("Quay lại", key="movie_detail_back"):
        navigate_back()


    # TIÊU ĐỀ PHIM
    movie_title = format_movie_title(movie["title"])
    st.html(
    f"""
    <div class="mm-detail-header">

        <div class="mm-detail-title">
            {safe_html(movie_title)}
        </div>

        <div class="mm-header-line"></div>

    </div>
    """
    )


    # TẢI DỮ LIỆU TMDB
    tmdb_id = normalize_tmdb_id(movie.get("tmdbId"))
    tmdb_info = {}
    trailer_url = None

    api_key = get_tmdb_api_key()

    if api_key and tmdb_id is not None:
        try:
            with st.spinner("Đang tải thông tin phim..."):
                tmdb_info, trailer_url = (load_movie_tmdb_detail(tmdb_id, api_key))
        except Exception as error:
            st.warning(
                "Không thể tải đầy đủ thông tin từ TMDb. "
                "Một số nội dung có thể chưa hiển thị."
            )
            tmdb_info = {}
            trailer_url = None


    # POSTER VÀ THÔNG TIN
    poster_data = ({tmdb_id: tmdb_info} if tmdb_id is not None and tmdb_info else {})

    poster_col, info_col = st.columns([0.9, 2.1], gap="large")

    with poster_col:
        show_movie_poster(movie, poster_data, width=None)
    with info_col:
        st.html(create_movie_info_html(movie, tmdb_info))
        homepage = tmdb_info.get("homepage")

        if homepage:
            st.link_button("Truy cập trang phim", homepage)


    # NỘI DUNG PHIM
    show_section_heading("Nội dung phim")
    overview = tmdb_info.get("overview")
    if overview:
        overview_html = safe_html(overview).replace("\n", "<br>")
        st.html(
            f"""
            <div class="mm-overview-card">
                {overview_html}
            </div>
            """
        )

    else:
        st.info("Chưa có mô tả phim từ TMDb.")


    # TRAILER
    show_section_heading("Trailer phim")
    if trailer_url:
        st.video(trailer_url)
    else:
        st.info("Chưa có trailer YouTube cho phim này.")


    # KHU VỰC ĐÁNH GIÁ
    show_section_heading("Đánh giá phim")
    st.html(
    """
    <div class="mm-rating-section">

        <div class="mm-rating-title">
            Chia sẻ cảm nhận của bạn!
        </div>

        <p class="mm-rating-description">
            Đánh giá phim để MovieMatch hiểu sở thích
            và cải thiện các đề xuất dành cho bạn.
        </p>

    </div>
    """
    )

    show_rating_widget(movie_id, username=st.session_state.get("username"))
