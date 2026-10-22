import pandas as pd
import streamlit as st
from src.data import load_movielens_data
from pages_ui.common import GENRE_TRANSLATIONS
from pages_ui.movie_display import load_poster_data, show_movie_poster

# =================================================
# 1. ĐỌC VÀ XỬ LÝ DỮ LIỆU PHIM
# =================================================

@st.cache_data
def load_movie_data():
    """
    Đọc dữ liệu từ data.py và bổ sung thông tin
    thống kê cho từng bộ phim.
    """
    # Đọc dữ liệu MovieLens
        # movies: Danh sách phim, bao gồm movieId, title, genres
        # ratings: Các đánh giá của người dùng, gồm userId, movieId, rating và timestamp
        # tags: Các nhãn do người dùng gán cho phim
        # links: Bảng ánh xạ movieId sang imdbId và tmdbId
        # ratings_with_movies: Bảng ratings đã được ghép với thông tin phim
    movies, ratings, tags, links, ratings_with_movies = load_movielens_data()

    # Bước 2: Tính số lượt đánh giá và điểm trung bình cho từng phim
    rating_stats = (
        ratings.groupby("movieId")
        .agg(
            # rating_count: tổng số lượt đánh giá.
            rating_count=("rating", "count"),
            # avg_rating: điểm trung bình của phim.
            avg_rating=("rating", "mean"),
        )
        .reset_index()
    )

    # Bước 3: Ghép thống kê đánh giá vào danh sách phim
    # Dùng left join để giữ lại cả những phim chưa có lượt đánh giá
    movie_data = movies.merge(rating_stats, on="movieId", how="left")

    # Bước 4: Ghép mã TMDB vào danh sách phim
    movie_data = movie_data.merge(
        links[["movieId", "tmdbId"]], on="movieId", how="left")

    # Bước 5: Xử lý những phim chưa có đánh giá
    # Nếu phim chưa có đánh giá thì rating_count = 0
    movie_data["rating_count"] = (
        movie_data["rating_count"].fillna(0).astype(int))

    # Bước 6: Chuẩn hóa kiểu dữ liệu của tmdbId
    # errors="coerce" chuyển giá trị không hợp lệ thành NaN.
    movie_data["tmdbId"] = pd.to_numeric(movie_data["tmdbId"], errors="coerce")

    # Bước 7: Trích xuất năm phát hành từ tên phim
    # Nếu tên phim không có năm ở cuối thì giá trị year sẽ là NaN.
    movie_data["year"] = pd.to_numeric(
        movie_data["title"].str.extract(r"\((\d{4})\)\s*$")[0], errors="coerce")

    # Trả về bảng dữ liệu phim đã xử lý
    return movie_data


# ==================================================
# 2. TẠO CÁC DANH MỤC PHIM
# ==================================================

def create_movie_sections(movie_data):
    """
    Tạo các danh mục phim từ dữ liệu MovieLens.
    """

    sections = []

    # Danh mục 1: Phim được đánh giá nhiều
    popular_movies = movie_data.sort_values(by=["rating_count", "avg_rating"], ascending=[
                                            False, False], na_position="last").head(10)
    sections.append(("Phim phổ biến", popular_movies))

    # Danh mục 2: Phim được đánh giá cao (Chỉ xét phim có ít nhất 20 lượt đánh giá)
    highly_rated = movie_data[movie_data["rating_count"] >= 20].sort_values(
        by=["avg_rating", "rating_count"], ascending=[False, False], na_position="last").head(10)
    sections.append(("Phim được đánh giá cao", highly_rated))

    # Danh mục 3: Phim phát hành gần đây trong dữ liệu
    recent_movies = movie_data[movie_data["year"].notna()].sort_values(
        by=["year", "rating_count"], ascending=[False, False], na_position="last").head(10)
    sections.append(("Phim phát hành gần đây trong dữ liệu", recent_movies))

    # Danh mục 4 trở đi: Phim theo thể loại
    genres = list(GENRE_TRANSLATIONS.items())

    # Tạo danh mục cho từng thể loại.
    for genre, section_title in genres:
        # Một phim có thể thuộc nhiều thể loại như Action|Adventure|Sci-Fi
        genre_movies = movie_data[movie_data["genres"].fillna(
            "").apply(lambda value: genre in value.split("|"))]

        # Ưu tiên phim được đánh giá nhiều.
        genre_movies = genre_movies.sort_values(
            by=["rating_count", "avg_rating"],
            ascending=[False, False],
            na_position="last",
        ).head(10)

        sections.append((section_title, genre_movies))

    return sections


# ==================================================
# 3. HIỂN THỊ MỘT DANH MỤC PHIM CUỘN NGANG
# ==================================================

def show_movie_section(section_title, movies, poster_data):
    """
    Hiển thị poster, tên phim và điểm đánh giá.
    """

    # Tiêu đề danh mục phim.
    st.subheader(section_title)

    # Nếu danh mục không có phim.
    if movies.empty:
        st.write("Chưa có phim trong danh mục này.")
        return

    # Hiển thị các phim trên một hàng ngang.
    with st.container(horizontal=True, wrap=True, gap="small"):
        # Duyệt từng bộ phim.
        for _, movie in movies.iterrows():
            with st.container(width=170):
                # Hiển thị poster bằng tiện ích dùng chung với trang gợi ý.
                show_movie_poster(movie, poster_data, width=150)

                # Hiển thị tên phim
                st.write(f"**{movie['title']}**")

                # Hiển thị điểm trung bình
                avg_rating = movie["avg_rating"]
                if pd.notna(avg_rating):
                    st.caption(f"Đánh giá: {avg_rating:.1f}/5")
                else:
                    st.caption("Chưa có điểm đánh giá")

                # Hiển thị số lượt đánh giá
                rating_count = movie["rating_count"]
                st.caption(f"{rating_count:,} lượt đánh giá")


# ==================================================
# 4. HIỂN THỊ TRANG CHỦ
# ==================================================

def show_home_page():
    st.title("CinaMatch")
    st.write(
        "Khám phá phim dựa trên dữ liệu đánh giá "
        "của cộng đồng MovieLens."
    )

    # Đọc dữ liệu thông qua data.py
    try:
        movie_data = load_movie_data()
    except Exception as error:
        st.error("Không thể tải hoặc đọc dữ liệu MovieLens.")
        st.write(
            "Hãy kiểm tra kết nối Internet, cấu trúc "
            "thư mục dataset và các file CSV."
        )
        # Hiển thị thông tin lỗi
        with st.expander("Chi tiết lỗi"):
            st.exception(error)
        return

    # Tạo danh mục phim
    sections = create_movie_sections(movie_data)

    # Tải poster bằng tiện ích dùng chung
    # Chỉ tải poster cho phim thực sự xuất hiện trong các danh mục.
    section_movie_frames = [section_movies for _,
                            section_movies in sections if not section_movies.empty]
    movies_to_display = (pd.concat(section_movie_frames, ignore_index=True)
                         if section_movie_frames else movie_data.iloc[0:0].copy())

    poster_data = load_poster_data(
        movies_to_display, spinner_text="Đang tải poster phim từ TMDB...", warn_if_missing_key=True)

    # Hiển thị các danh mục phim
    for section_title, section_movies in sections:
        show_movie_section(section_title, section_movies, poster_data)
