import pandas as pd
import streamlit as st

from pages_ui.movie_display import load_poster_data, show_movie_poster
from src.common import context, enrich, GENRE_TRANSLATIONS, format_movie_title, shorten_text, translate_genres


PAGE_SIZE = 24


def _open_movie_detail(movie_id):
    """Chuyển sang trang chi tiết và ghi nhớ trang tìm kiếm."""
    st.query_params["movie_id"] = str(int(movie_id))
    st.query_params["return_page"] = "search"
    st.rerun()


def show_search_results(movies, poster_data, *, key_prefix="search"):
    """Hiển thị kết quả dạng lưới, kèm điểm và nút xem chi tiết."""
    if movies is None or movies.empty:
        st.info("Không tìm thấy phim phù hợp.")
        return

    columns_per_row = 5
    for start in range(0, len(movies), columns_per_row):
        row = movies.iloc[start:start + columns_per_row]
        columns = st.columns(columns_per_row, gap="small")

        for column, (_, movie) in zip(columns, row.iterrows()):
            movie_id = int(movie["movieId"])
            with column:
                with st.container(border=True):
                    show_movie_poster(movie, poster_data, width=None)

                    st.write(f"**{shorten_text(format_movie_title(movie['title']), max_chars=20)}**")
                    st.caption(shorten_text(translate_genres(movie.get("genres", "")), max_chars=20))

                    rating = movie.get("mean", movie.get("avg_rating"))
                    count_value = movie.get("count", movie.get("rating_count", 0))
                    count = int(count_value) if pd.notna(count_value) else 0

                    if pd.notna(rating) and count:
                        st.caption(f":star: {float(rating):.1f}/5 · {count:,} lượt")
                    else:
                        st.caption("Chưa có đánh giá")

                    if st.button("Xem chi tiết", key=f"{key_prefix}_detail_{movie_id}", width="stretch"):
                        st.query_params["movie_id"] = str(movie_id)
                        st.query_params["return_page"] = "Tìm kiếm"
                        _open_movie_detail(movie_id)


def show_search():
    st.title("Khám phá phim")
    st.caption("Tìm kiếm, lọc thể loại và sắp xếp phim theo đánh giá cộng đồng.")

    try:
        movies, ratings, _ = context()
        df = enrich(movies, ratings)
    except Exception as error:
        st.error("Không thể tải dữ liệu phim.")
        with st.expander("Chi tiết lỗi"):
            st.exception(error)
        return

    query = st.text_input(
        "Tìm kiếm phim",
        placeholder="Nhập tên phim bạn muốn tìm...",
        key="search",
    )

    genres = sorted({
        genre
        for value in movies["genres"].dropna()
        for genre in str(value).split("|")
        if genre and genre != "(no genres listed)"
    })

    with st.expander("Bộ lọc và sắp xếp", expanded=True):
        col_genre, col_sort = st.columns(2)

        with col_genre:
            genre = st.selectbox(
                "Thể loại",
                ["Tất cả"] + genres,
                format_func=lambda value: (
                    "Tất cả thể loại"
                    if value == "Tất cả"
                    else GENRE_TRANSLATIONS.get(value, value)
                ),
                key="search_genre",
            )

        with col_sort:
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

    if query.strip():
        df = df[
            df["title"].str.contains(
                query.strip(),
                case=False,
                regex=False,
                na=False,
            )
        ]

    if genre != "Tất cả":
        df = df[
            df["genres"]
            .fillna("")
            .str.split("|")
            .apply(lambda values: genre in values)
        ]

    sort_options = {
        "Phổ biến nhất": ("count", False),
        "Ít phổ biến nhất": ("count", True),
        "Điểm cao nhất": ("score", False),
        "Điểm thấp nhất": ("score", True),
        "Tên A–Z": ("title", True),
    }
    sort_column, ascending = sort_options[sort]
    df = df.sort_values(sort_column, ascending=ascending, kind="stable")

    # Khi bộ lọc thay đổi, quay số lượng hiển thị về trang đầu tiên.
    filter_key = (query.strip(), genre, sort)
    if st.session_state.get("search_filter_key") != filter_key:
        st.session_state["search_filter_key"] = filter_key
        st.session_state["search_visible_movies"] = PAGE_SIZE

    visible_count = st.session_state.get("search_visible_movies", PAGE_SIZE)
    displayed = df.head(visible_count).copy()

    st.subheader("Kết quả tìm kiếm")
    st.caption(
        f"Tìm thấy {len(df):,} phim · Đang hiển thị {len(displayed):,} phim"
    )

    if displayed.empty:
        st.info("Không tìm thấy phim phù hợp. Hãy thử từ khóa hoặc thể loại khác.")
        return

    poster_data = load_poster_data(
        displayed,
        spinner_text="Đang tải poster phim...",
        warn_if_missing_key=True,
    )
    show_search_results(displayed, poster_data)

    if visible_count < len(df):
        if st.button("⬇ Tải thêm 24 phim", width="stretch"):
            st.session_state["search_visible_movies"] = min(
                visible_count + PAGE_SIZE,
                len(df),
            )
            st.rerun()
