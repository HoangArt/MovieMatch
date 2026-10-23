import streamlit as st
import pandas as pd
from pages_ui.movie_display import (
    load_poster_data,
    show_movie_poster,
)

from src.common import (
    context,
    enrich,
    GENRE_TRANSLATIONS,
    shorten_text,
)


# ==================================================
# 1. HIỂN THỊ DANH SÁCH PHIM TÌM KIẾM
# ==================================================

def show_search_results(movies, poster_data):
    """
    Hiển thị poster, tên phim, điểm đánh giá,
    số lượt đánh giá và nút xem chi tiết.
    """

    # Kiểm tra danh sách phim
    if movies.empty:
        st.info("Không tìm thấy phim phù hợp.")
        return

    # Hiển thị phim theo hàng ngang
    with st.container(
        horizontal=True,
        wrap=True,
        gap="small",
    ):
        for _, movie in movies.iterrows():

            # Mỗi phim có một khung riêng
            with st.container(width=170):

                # 1. Hiển thị poster
                show_movie_poster(
                    movie,
                    poster_data,
                    width=150,
                )

                # 2. Rút gọn tên phim
                title = shorten_text(
                    movie.get("title", ""),
                    max_chars=23,
                )

                st.write(f"**{title}**")

                # 3. Hiển thị điểm đánh giá trung bình
                avg_rating = movie.get("avg_rating")

                if pd.notna(avg_rating):
                    st.caption(
                        f"Đánh giá: {avg_rating:.1f}/5"
                    )
                else:
                    st.caption("Chưa có điểm đánh giá")

                # 4. Hiển thị số lượt đánh giá
                rating_count = movie.get(
                    "rating_count",
                    movie.get("count", 0),
                )

                if pd.isna(rating_count):
                    rating_count = 0

                try:
                    rating_count = int(rating_count)
                except (TypeError, ValueError, OverflowError):
                    rating_count = 0

                st.caption(
                    f"{rating_count:,} lượt đánh giá"
                )

                # 5. Lấy ID phim
                movie_id = movie.get("movieId")

                # Hỗ trợ trường hợp cột có tên movie_id
                if pd.isna(movie_id):
                    movie_id = movie.get("movie_id")

                # 6. Tạo nút xem chi tiết
                if pd.notna(movie_id):
                    try:
                        movie_id = int(movie_id)
                    except (TypeError, ValueError, OverflowError):
                        continue

                    if st.button(
                        "Xem chi tiết",
                        key=f"detail_search_{movie_id}",
                        width="stretch",
                    ):
                        # Chuyển đến trang chi tiết phim
                        st.query_params["movie_id"] = str(movie_id)

                        # Ghi nhớ trang trước đó
                        st.query_params["return_page"] = "search"

                        # Chạy lại ứng dụng
                        st.rerun()


# ==================================================
# 2. TRANG TÌM KIẾM PHIM
# ==================================================

def show_search():
    st.title("Khám phá phim")

    st.caption(
        "Tìm kiếm những bộ phim yêu thích của bạn."
    )

    # --------------------------------------------------
    # Đọc dữ liệu
    # --------------------------------------------------

    try:
        movies, ratings, _ = context()
        df = enrich(movies, ratings)

    except Exception as error:
        st.error("Không thể tải dữ liệu phim.")
        with st.expander("Chi tiết lỗi"):
            st.exception(error)
        return

    # --------------------------------------------------
    # Thanh tìm kiếm
    # --------------------------------------------------

    q = st.text_input(
        "Tìm kiếm phim",
        placeholder="Nhập tên phim bạn muốn tìm...",
        key="search",
        label_visibility="collapsed",
    )

    # --------------------------------------------------
    # Danh sách thể loại
    # --------------------------------------------------

    genres = sorted({
        genre
        for value in movies["genres"].dropna()
        for genre in str(value).split("|")
        if genre and genre != "(no genres listed)"
    })

    genre_options = ["Tất cả"] + genres

    # --------------------------------------------------
    # Bộ lọc và sắp xếp
    # --------------------------------------------------

    with st.expander("Bộ lọc và sắp xếp"):

        col1, col2 = st.columns(2)

        with col1:
            genre = st.selectbox(
                "Thể loại",
                genre_options,
                format_func=lambda value: (
                    "Tất cả thể loại"
                    if value == "Tất cả"
                    else GENRE_TRANSLATIONS.get(value, value)
                ),
                key="search_genre",
            )

        with col2:
            sort = st.selectbox(
                "Sắp xếp",
                [
                    "Phổ biến nhất",
                    "Ít phổ biến nhất",
                    "Điểm cao nhất",
                    "Điểm thấp nhất",
                    "Tên A–Z",
                ],
                key="search_sort",
            )

    # --------------------------------------------------
    # Lọc theo tên phim
    # --------------------------------------------------

    if q.strip():
        df = df[
            df["title"].str.contains(
                q.strip(),
                case=False,
                regex=False,
                na=False,
            )
        ]

    # --------------------------------------------------
    # Lọc theo thể loại
    # --------------------------------------------------

    if genre != "Tất cả":
        df = df[
            df["genres"]
            .fillna("")
            .str.split("|")
            .apply(lambda values: genre in values)
        ]

    # --------------------------------------------------
    # Sắp xếp kết quả
    # --------------------------------------------------

    if sort == "Phổ biến nhất":
        df = df.sort_values(
            "count",
            ascending=False,
        )

    elif sort == "Ít phổ biến nhất":
        df = df.sort_values(
            "count",
            ascending=True,
        )

    elif sort == "Điểm cao nhất":
        df = df.sort_values(
            "score",
            ascending=False,
        )

    elif sort == "Điểm thấp nhất":
        df = df.sort_values(
            "score",
            ascending=True,
        )

    else:
        df = df.sort_values(
            "title",
            ascending=True,
        )

    # --------------------------------------------------
    # Thông tin kết quả tìm kiếm
    # --------------------------------------------------

    st.subheader("Kết quả tìm kiếm")

    st.caption(
        f"Tìm thấy {len(df):,} phim · "
        "Hiển thị tối đa 24 phim"
    )

    if df.empty:
        st.info(
            "Không tìm thấy phim phù hợp. "
            "Hãy thử tên phim hoặc thể loại khác."
        )
        return

    # Chỉ hiển thị tối đa 24 phim
    display_df = df.head(24).copy()

    # --------------------------------------------------
    # Tải poster cho các phim sẽ hiển thị
    # --------------------------------------------------

    poster_data = load_poster_data(
        display_df,
        spinner_text="Đang tải poster phim...",
        warn_if_missing_key=True,
    )

    # --------------------------------------------------
    # Hiển thị kết quả và nút chi tiết
    # --------------------------------------------------

    show_search_results(
        display_df,
        poster_data,
    )