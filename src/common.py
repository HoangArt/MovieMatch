import streamlit as st
import re
import pandas as pd
import zipfile
import requests
from pathlib import Path
from io import BytesIO

# ==========================================
# 1. ĐƯỜNG DẪN DỮ LIỆU
# ==========================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"

DATASET_DIR = DATA_DIR / "ml-latest-small"

MOVIES_FILE = DATASET_DIR / "movies.csv"
RATINGS_FILE = DATASET_DIR / "ratings.csv"
TAGS_FILE = DATASET_DIR / "tags.csv"
LINKS_FILE = DATASET_DIR / "links.csv"

DATASET_URL = (
    "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
)


# =========================================
# 2. TẢI DỮ LIỆU NẾU CÁC TỆP KHÔNG TỒN TẠI
# =========================================
def ensure_dataset_exists():
    if MOVIES_FILE.exists() and RATINGS_FILE.exists() and TAGS_FILE.exists() and LINKS_FILE.exists():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    response = requests.get(DATASET_URL, timeout=60)
    response.raise_for_status()

    with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
        zip_file.extractall(DATA_DIR)

    if not MOVIES_FILE.exists() or not RATINGS_FILE.exists() or not TAGS_FILE.exists() or not LINKS_FILE.exists():
        raise FileNotFoundError(
            "Không tìm thấy một hoặc nhiều tệp dữ liệu."
            " Hãy kiểm tra lại thư mục dữ liệu."
        )


# ==========================================
# 3. ĐỌC DỮ LIỆU TỪ CÁC TỆP CSV
# ==========================================
def load_movielens_data():
    ensure_dataset_exists()

    movies = pd.read_csv(MOVIES_FILE)
    ratings = pd.read_csv(RATINGS_FILE)
    tags = pd.read_csv(TAGS_FILE)
    links = pd.read_csv(LINKS_FILE)

    # Chuyển đổi cột 'timestamp' trong ratings_df sang định dạng datetime
    ratings['timestamp'] = pd.to_datetime(ratings['timestamp'], unit='s')
    tags['timestamp'] = pd.to_datetime(tags['timestamp'], unit='s')

    # Ghép điểm đánh giá với tên và thể loại phim
    ratings_with_movies = ratings.merge(movies, on='movieId', how='left')

    return movies, ratings, tags, links, ratings_with_movies

# ==========================================
# 4. ĐỌC DỮ LIỆU MOVIELENS
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

    movies_path = MOVIES_FILE
    ratings_path = RATINGS_FILE
    links_path = LINKS_FILE

    for path in (movies_path, ratings_path, links_path):
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


# =========================================
# 5. LẤY DỮ LIỆU PHIM
# =========================================
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

# ==========================================
# 6. TÍNH ĐIỂM ĐÁNH GIÁ CHO PHIM
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
# 7. DỊCH TÊN THỂ LOẠI
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
# 8. CHUẨN HÓA TÊN PHIM
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
# 9. RÚT NGẮN NỘI DUNG
# ==========================================
def shorten_text(text, max_chars=20):
    """
    Rút gọn văn bản nếu vượt quá số ký tự cho phép.
    Ví dụ: Shawshank Redemption, The (1994) -> Shawshank Redemption...
    """

    if pd.isna(text):
        return ""

    text = str(text).strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars - 3].rstrip() + "..."


# ==========================================
# 10. HIỂN THỊ THÔNG TIN CHI TIẾT PHIM
# ==========================================
def open_movie_detail(movie_id):
    """Lưu phim được chọn và chuyển sang trang chi tiết."""
    current_page = st.session_state.get("displayed_page")
    if current_page not in {
        "Trang chủ", "Tìm kiếm", "Gợi ý phim", "Phim yêu thích", "Thống kê", "Thiết lập sở thích"
    }:
        current_page = st.session_state.get("main_navigation", "Trang chủ")
    st.session_state["return_page"] = current_page
    st.session_state["selected_movie"] = str(int(movie_id))
    st.rerun()


# =========================================
# 11. HIỂN THỊ LƯỚI PHIM
# =========================================
def movie_grid(movies_df, key, *, columns_count=5, limit=20, score_column=None, score_label="Điểm dự đoán"):
    """Hiển thị poster/phim và nút chi tiết; dùng chung cho tìm kiếm và gợi ý."""
    from pages_ui.movie_display import load_poster_data, show_movie_poster

    if movies_df is None or movies_df.empty:
        st.info("Chưa có phim phù hợp.")
        return

    displayed_movies = movies_df.head(limit).copy()
    poster_data = load_poster_data(displayed_movies, spinner_text="Đang tải poster phim...", warn_if_missing_key=False)

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

                    if st.button("Xem chi tiết", key=f"{key}_detail_{movie_id}", width="stretch"):
                        open_movie_detail(movie_id)



def movie_carousel(movies_df, key, limit=20):
    """
    Hiển thị phim theo dạng lưới nhiều cột.

    """
    movie_grid(movies_df, key, columns_count=5, limit=limit)