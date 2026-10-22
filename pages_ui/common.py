from pathlib import Path
import re

import pandas as pd
import streamlit as st

from src.tmdb import get_movie_poster


# ==========================================
# 1. ĐƯỜNG DẪN DỮ LIỆU
# ==========================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data" / "ml-latest-small"


# ==========================================
# 2. ĐỌC DỮ LIỆU MOVIELENS
# ==========================================
@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def context():
    """
    Đọc movies.csv, ratings.csv và links.csv.

    Trả về:
        movies: thông tin phim kèm tmdbId
        ratings: các lượt đánh giá
        links: ánh xạ ID phim
    """

    movies_path = DATA_DIR / "movies.csv"
    ratings_path = DATA_DIR / "ratings.csv"
    links_path = DATA_DIR / "links.csv"

    for path in (
        movies_path,
        ratings_path,
        links_path,
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file dữ liệu: {path}"
            )

    movies = pd.read_csv(movies_path)
    ratings = pd.read_csv(ratings_path)
    links = pd.read_csv(links_path)

    # Chuẩn hóa ID để có thể ghép dữ liệu.
    movies["movieId"] = pd.to_numeric(
        movies["movieId"],
        errors="coerce",
    )

    ratings["movieId"] = pd.to_numeric(
        ratings["movieId"],
        errors="coerce",
    )

    links["movieId"] = pd.to_numeric(
        links["movieId"],
        errors="coerce",
    )

    links["tmdbId"] = pd.to_numeric(
        links["tmdbId"],
        errors="coerce",
    )

    # Đưa tmdbId vào bảng phim.
    movies = movies.merge(
        links[["movieId", "tmdbId"]],
        on="movieId",
        how="left",
    )

    movies["genres"] = (
        movies["genres"]
        .fillna("")
        .astype(str)
    )

    ratings["rating"] = pd.to_numeric(
        ratings["rating"],
        errors="coerce",
    )

    ratings = ratings.dropna(
        subset=["movieId", "rating"]
    )

    movies = movies.dropna(
        subset=["movieId"]
    )

    movies["movieId"] = movies["movieId"].astype(int)
    ratings["movieId"] = ratings["movieId"].astype(int)
    links["movieId"] = links["movieId"].astype(int)

    return movies, ratings, links


# ==========================================
# 3. TÍNH ĐIỂM ĐÁNH GIÁ CHO PHIM
# ==========================================
@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def enrich(movies, ratings):
    """
    Bổ sung các thông số đánh giá cho mỗi phim.

    mean  : điểm trung bình
    count : số lượt đánh giá
    score : điểm có điều chỉnh theo số lượt đánh giá
    """

    # Tính điểm trung bình và số lượt đánh giá
    # của từng movieId.
    stats = (
        ratings.groupby("movieId")["rating"]
        .agg(
            mean="mean",
            count="count",
        )
        .reset_index()
    )

    df = movies.merge(
        stats,
        on="movieId",
        how="left",
    )

    global_mean = (
        float(ratings["rating"].mean())
        if not ratings.empty
        else 0.0
    )

    df["mean"] = df["mean"].fillna(global_mean)

    df["count"] = (
        df["count"]
        .fillna(0)
        .astype(int)
    )

    # Điểm trung bình có điều chỉnh:
    #
    # score = (v / (v + m)) * R
    #       + (m / (v + m)) * C
    #
    # R: điểm trung bình của phim
    # v: số lượt đánh giá của phim
    # m: ngưỡng số lượt đánh giá
    # C: điểm trung bình toàn bộ dữ liệu

    m = 50
    v = df["count"]
    R = df["mean"]
    C = global_mean

    df["score"] = (
        (v / (v + m)) * R
        + (m / (v + m)) * C
    )

    return df


# ==========================================
# 4. DỊCH TÊN THỂ LOẠI
# ==========================================
GENRE_TRANSLATIONS = {
    "Action": "Hành động",
    "Adventure": "Phiêu lưu",
    "Animation": "Hoạt hình",
    "Children": "Thiếu nhi",
    "Comedy": "Hài",
    "Crime": "Tội phạm",
    "Documentary": "Tài liệu",
    "Drama": "Chính kịch",
    "Fantasy": "Giả tưởng",
    "Film-Noir": "Phim noir",
    "Horror": "Kinh dị",
    "IMAX": "IMAX",
    "Musical": "Nhạc kịch",
    "Mystery": "Bí ẩn",
    "Romance": "Lãng mạn",
    "Sci-Fi": "Khoa học viễn tưởng",
    "Thriller": "Giật gân",
    "War": "Chiến tranh",
    "Western": "Viễn Tây",
    "(no genres listed)": "Chưa phân loại",
}


def translate_genres(genres):
    """
    Chuyển chuỗi thể loại tiếng Anh
    sang tiếng Việt.
    """

    if not genres:
        return "Chưa phân loại"

    genre_list = str(genres).split("|")

    translated = [
        GENRE_TRANSLATIONS.get(
            genre,
            genre,
        )
        for genre in genre_list
        if genre
    ]

    return " · ".join(translated) or "Chưa phân loại"


# ==========================================
# 5. CHUẨN HÓA TÊN PHIM
# ==========================================
def format_movie_title(title):
    """
    Ví dụ:
    Shawshank Redemption, The (1994) -> The Shawshank Redemption (1994)
    """

    title = str(title).strip()

    match = re.search(
        r"\((\d{4})\)\s*$",
        title,
    )

    year = f" ({match.group(1)})" if match else ""

    name = re.sub(
        r"\s*\(\d{4}\)\s*$",
        "",
        title,
    ).strip()

    for article in ("The", "An", "A"):
        suffix = f", {article}"

        if name.endswith(suffix):
            name = f"{article} {name[:-len(suffix)]}"
            break

    return name + year


# ==========================================
# 6. HIỂN THỊ DANH SÁCH PHIM
# ==========================================
def open_movie_detail(movie_id):
    """Lưu phim được chọn và chuyển sang trang chi tiết."""
    current_page = st.session_state.get("displayed_page")
    if current_page not in {
        "Trang chủ", "Tìm kiếm", "Gợi ý phim", "Phim yêu thích", "Thống kê", "Thiết lập sở thích"
    }:
        current_page = st.session_state.get("main_navigation", "Trang chủ")
    st.session_state["return_page"] = current_page
    st.session_state["selected_movie"] = int(movie_id)
    st.session_state["page"] = "Chi tiết phim"
    st.rerun()


def movie_grid(
    movies_df,
    key,
    *,
    columns_count=5,
    limit=20,
    score_column=None,
    score_label="Điểm dự đoán",
):
    """Hiển thị poster/phim và nút chi tiết; dùng chung cho tìm kiếm và gợi ý."""
    from pages_ui.movie_display import load_poster_data, show_movie_poster

    if movies_df is None or movies_df.empty:
        st.info("Chưa có phim phù hợp.")
        return

    displayed_movies = movies_df.head(limit).copy()
    poster_data = load_poster_data(
        displayed_movies,
        spinner_text="Đang tải poster phim...",
        warn_if_missing_key=False,
    )

    for start in range(0, len(displayed_movies), columns_count):
        batch = displayed_movies.iloc[start:start + columns_count]
        columns = st.columns(columns_count, gap="small")
        for column, (_, movie) in zip(columns, batch.iterrows()):
            movie_id = int(movie["movieId"])
            with column:
                with st.container(border=True):
                    show_movie_poster(movie, poster_data, width=None)
                    st.write(f"**{format_movie_title(movie['title'])}**")
                    st.caption(translate_genres(movie.get("genres", "")))

                    mean_rating = movie.get("mean")
                    count_value = movie.get("count", 0)
                    rating_count = int(count_value) if pd.notna(count_value) else 0
                    if pd.notna(mean_rating) and rating_count > 0:
                        st.caption(f"⭐ {float(mean_rating):.1f}/5 · {rating_count:,} lượt")
                    elif "rating_count" in movie.index:
                        st.caption(f"{int(movie.get('rating_count', 0)):,} lượt đánh giá")

                    if score_column and score_column in movie.index and pd.notna(movie[score_column]):
                        score = float(movie[score_column])
                        if score_column == "similarity":
                            st.metric(score_label, f"{score * 100:.1f}%")
                        else:
                            st.metric(score_label, f"{score:.2f}/5")

                    if st.button(
                        "Xem chi tiết",
                        key=f"{key}_detail_{movie_id}",
                        use_container_width=True,
                    ):
                        open_movie_detail(movie_id)



def movie_carousel(movies_df, key, limit=20):
    """
    Hiển thị phim theo dạng lưới nhiều cột.

    """

    movie_grid(movies_df, key, columns_count=5, limit=limit)