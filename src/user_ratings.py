from datetime import datetime, timezone
from src.database import db_connection

VALID_RATINGS = tuple(value / 2 for value in range(1, 11))

"""Lưu và truy vấn điểm đánh giá do người dùng MovieMatch gửi."""

def init_ratings_db():
    """Tạo bảng đánh giá trong cùng SQLite database của ứng dụng."""
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                movie_id INTEGER NOT NULL,
                rating REAL NOT NULL CHECK (
                    rating >= 0.5
                    AND rating <= 5.0
                    AND rating * 2 = CAST(rating * 2 AS INTEGER)
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(username, movie_id),
                FOREIGN KEY(username)
                    REFERENCES users(username)
                    ON DELETE CASCADE
            )
            """
        )


def save_user_rating(username, movie_id, rating):
    """Lưu mới hoặc cập nhật điểm của một người dùng cho một phim."""
    if not username or not str(username).strip():
        raise ValueError("Bạn cần đăng nhập để đánh giá.")

    username = str(username).strip().lower()
    movie_id = int(movie_id)
    rating = float(rating)

    if rating not in VALID_RATINGS:
        raise ValueError(
            "Điểm đánh giá phải từ 0,5 đến 5 sao, với bước nhảy 0,5."
        )

    now = datetime.now(timezone.utc).isoformat()

    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_ratings (
                username, movie_id, rating, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username, movie_id)
            DO UPDATE SET
                rating = excluded.rating,
                updated_at = excluded.updated_at
            """,
            (username, movie_id, rating, now, now),
        )


def get_user_rating(username, movie_id):
    """Lấy điểm mà người dùng hiện tại đã chấm cho một phim."""
    if not username:
        return None

    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT rating
            FROM user_ratings
            WHERE username = ? AND movie_id = ?
            """,
            (str(username).strip().lower(), int(movie_id)),
        ).fetchone()

    return float(row["rating"]) if row else None


def get_user_ratings(username):
    """Lấy toàn bộ phim người dùng đã chấm, mới cập nhật trước."""
    if not username:
        return []

    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT movie_id, rating, updated_at
            FROM user_ratings
            WHERE username = ?
            ORDER BY updated_at DESC
            """,
            (str(username).strip().lower(),),
        ).fetchall()

    return [dict(row) for row in rows]


def delete_user_rating(username, movie_id):
    """Xóa điểm đánh giá của người dùng cho một phim."""
    if not username:
        return

    with db_connection() as conn:
        conn.execute(
            """
            DELETE FROM user_ratings
            WHERE username = ? AND movie_id = ?
            """,
            (str(username).strip().lower(), int(movie_id)),
        )


def get_community_rating(movie_id):
    """Tính điểm trung bình và số lượt đánh giá trên MovieMatch."""
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT AVG(rating) AS average_rating, COUNT(*) AS rating_count
            FROM user_ratings
            WHERE movie_id = ?
            """,
            (int(movie_id),),
        ).fetchone()

    if not row or not row["rating_count"]:
        return None, 0

    return round(float(row["average_rating"]), 2), int(row["rating_count"])
