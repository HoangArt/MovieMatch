import streamlit as st
from pages_ui.common import context, enrich, GENRE_TRANSLATIONS, movie_carousel

def show_search():
    st.title("Khám phá phim")
    st.caption("Tìm kiếm những bộ phim yêu thích của bạn.")

    # Tải dữ liệu MovieLens
    movies, ratings, _ = context()
    df = enrich(movies, ratings)

    # Thanh tìm kiếm kiểu Netflix
    q = st.text_input("Tìm kiếm phim", placeholder="Nhập tên phim bạn muốn tìm...",
                      key="search", label_visibility="collapsed")

    # Danh sách thể loại
    genres = sorted({g for s in movies["genres"].dropna() for g in str(
        s).split("|") if g != "(no genres listed)"})

    genre_options = ["Tất cả"] + genres

    # Bộ lọc thu gọn
    with st.expander("Bộ lọc và sắp xếp"):
        col1, col2 = st.columns(2)
        with col1:
            genre = st.selectbox(
                "Thể loại", genre_options, format_func=lambda g:
                ("Tất cả thể loại"if g ==
                 "Tất cả" else GENRE_TRANSLATIONS.get(g, g)),
                key="search_genre"
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

    # Lọc theo tên phim
    if q.strip():
        df = df[df["title"].str.contains(q.strip(), case=False, regex=False, na=False)]

    # Lọc theo thể loại
    if genre != "Tất cả":
        df = df[df["genres"].fillna("").str.split("|").apply(lambda values: genre in values)]

    # Sắp xếp kết quả
    if sort == "Phổ biến nhất":
        df = df.sort_values("count", ascending=False)
    elif sort == "Ít phổ biến nhất":
        df = df.sort_values("count", ascending=True)
    elif sort == "Điểm cao nhất":
        df = df.sort_values("score", ascending=False)
    elif sort == "Điểm thấp nhất":
        df = df.sort_values("score", ascending=True)
    else:
        df = df.sort_values("title")

    st.text("Kết quả tìm kiếm")
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
    
    # Hiển thị kết quả
    movie_carousel(df, "search", limit=24)
