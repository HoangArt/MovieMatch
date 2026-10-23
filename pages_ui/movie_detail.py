import streamlit as st
import pandas as pd
from src.common import load_movie_data, format_movie_title, translate_genres
from src.tmdb import fetch_tmdb_movie, get_tmdb_api_key

def show_movie_detail_page(movie_id):
    """Hiển thị thông tin chi tiết của một bộ phim."""

    # 1. Tìm phim trong dữ liệu MovieLens
    movie_data = load_movie_data()

    movie_rows = movie_data[movie_data["movieId"] == movie_id]

    # Nếu phim không tồn tại trong tập dữ liệu
    if movie_rows.empty:
        st.error("Không tìm thấy bộ phim này.")
        if st.button("Quay lại trang chủ"):
            st.query_params.clear()
            st.rerun()
        return

    # Chuyển dòng dữ liệu thành Series để dễ sử dụng
    movie = movie_rows.iloc[0]

    # 2. Lấy thông tin bổ sung từ TMDB
    tmdb_id = movie.get("tmdbId")
    tmdb_info = {}

    if pd.notna(tmdb_id):
        try:
            tmdb_id = int(float(tmdb_id))
            api_key = get_tmdb_api_key()

            if api_key:
                tmdb_info = fetch_tmdb_movie(tmdb_id, api_key)
        except (TypeError, ValueError, OverflowError):
            tmdb_info = {}

    # 3. Nút quay lại
    if st.button("Quay lại"):
        st.query_params.clear()
        st.rerun()

    # 4. Tiêu đề phim
    st.title(format_movie_title(movie["title"]))

    # 5. Chia giao diện thành hai cột
    poster_col, info_col = st.columns([1, 2])
    # Cột poster
    with poster_col:
        poster_url = tmdb_info.get("poster_url")

        if poster_url:
            st.image(poster_url, width="stretch")
        else:
            st.info("Phim chưa có poster.")

    # Cột thông tin
    with info_col:
        # Năm phát hành
        year = movie.get("year")

        if pd.notna(year):
            st.write(f"**Năm phát hành:** {int(year)}")

        # Thể loại
        genres = translate_genres(movie.get("genres", ""))
        st.write(f"**Thể loại:** {genres}")

        # Điểm đánh giá từ MovieLens
        avg_rating = movie.get("avg_rating")
        rating_count = movie.get("rating_count", 0)

        if pd.notna(avg_rating):
            st.write(f"**Điểm MovieLens:** {avg_rating:.1f}/5")

        st.write(f"**Số lượt đánh giá:** {int(rating_count):,}")

        # Thông tin bổ sung từ TMDB
        runtime = tmdb_info.get("runtime")

        if runtime:
            st.write(f"**Thời lượng:** {runtime} phút")

        tmdb_rating = tmdb_info.get("tmdb_vote_average")

        if tmdb_rating is not None:
            st.write(f"**Điểm TMDB:** {tmdb_rating}/10")

        original_language = tmdb_info.get("original_language")

        if original_language:
            st.write(
                f"**Ngôn ngữ gốc:** {original_language}"
            )

        tagline = tmdb_info.get("tagline")

        if tagline:
            st.caption(tagline)

    # 6. Mô tả phim
    st.divider()
    st.subheader("Nội dung phim")

    overview = tmdb_info.get("overview", "")

    if overview:
        st.write(overview)
    else:
        st.info(
            "Chưa có mô tả phim từ TMDB. "
            "Bạn có thể kiểm tra lại TMDB API key hoặc dữ liệu phim."
        )

    # 7. Liên kết trang phim trên TMDB nếu có
    homepage = tmdb_info.get("homepage")

    if homepage:
        st.link_button("Trang phim bên ngoài", homepage)
