from pathlib import Path
from io import BytesIO
import zipfile
import requests
import pandas as pd

# Đường dẫn dự án
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

# Tải dữ liệu nếu các tệp không tồn tại


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

# Đọc dữ liệu từ các tệp CSV
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