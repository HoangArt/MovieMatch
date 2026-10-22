from pathlib import Path
from contextlib import contextmanager
import sqlite3
import hashlib
import secrets
import hmac


# Lưu database ngay trong thư mục dự án thay vì phụ thuộc thư mục chạy lệnh.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "movie_recommendations.db"

# Số vòng lặp khi băm mật khẩu.
PBKDF2_ITERATIONS = 600_000

def get_connection():
    """Mở kết nối SQLite đến database của ứng dụng."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def db_connection():
    """Context manager luôn đóng kết nối sau mỗi thao tác database."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Tạo các bảng tài khoản, phim yêu thích và trạng thái onboarding."""
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_favorite_movies (
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_onboarding (
                user_id INTEGER PRIMARY KEY,
                completed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )


def hash_password(password, salt):
    """Băm mật khẩu bằng PBKDF2-HMAC-SHA256."""
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return password_hash.hex()


def register_user(username, email, password):
    """Tạo tài khoản mới; chỉ lưu salt và mật khẩu đã băm."""
    username = username.strip().lower()
    email = email.strip().lower()
    salt = secrets.token_bytes(16)
    password_hash = hash_password(password, salt)

    try:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (username, email, password_salt, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (username, email, salt.hex(), password_hash),
            )
        return True, "Đăng ký tài khoản thành công!"
    except sqlite3.IntegrityError:
        return False, "Tên đăng nhập hoặc email đã tồn tại."


def authenticate_user(username, password):
    """Xác thực tài khoản và trả về thông tin cần dùng trong session."""
    username = username.strip().lower()
    with db_connection() as conn:
        user = conn.execute(
            """
            SELECT id, username, password_salt, password_hash
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if user is None:
        return None

    salt = bytes.fromhex(user["password_salt"])
    entered_hash = hash_password(password, salt)

    if hmac.compare_digest(entered_hash, user["password_hash"]):
        return {"id": user["id"], "username": user["username"]}
    return None


def is_onboarding_completed(user_id):
    """Kiểm tra người dùng đã hoàn tất bước chọn sở thích ban đầu chưa."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT completed FROM user_onboarding WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
    return bool(row and row["completed"])


def get_user_favorite_movie_ids(user_id):
    """Lấy danh sách movieId yêu thích của riêng một tài khoản."""
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT movie_id
            FROM user_favorite_movies
            WHERE user_id = ?
            ORDER BY position, created_at, movie_id
            """,
            (int(user_id),),
        ).fetchall()
    return [int(row["movie_id"]) for row in rows]


def save_user_favorite_movies(user_id, movie_ids):
    """Thay thế danh sách phim yêu thích và đánh dấu onboarding hoàn tất."""
    user_id = int(user_id)
    # Loại trùng nhưng vẫn giữ thứ tự người dùng chọn.
    unique_movie_ids = list(dict.fromkeys(int(movie_id) for movie_id in movie_ids))

    with db_connection() as conn:
        conn.execute(
            "DELETE FROM user_favorite_movies WHERE user_id = ?",
            (user_id,),
        )
        conn.executemany(
            """
            INSERT INTO user_favorite_movies (user_id, movie_id, position)
            VALUES (?, ?, ?)
            """,
            [
                (user_id, movie_id, position)
                for position, movie_id in enumerate(unique_movie_ids)
            ],
        )
        conn.execute(
            """
            INSERT INTO user_onboarding (user_id, completed, updated_at)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                completed = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id,),
        )


def mark_onboarding_completed(user_id):
    """Cho phép bỏ qua bước chọn phim; không xóa sở thích đang có."""
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_onboarding (user_id, completed, updated_at)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                completed = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (int(user_id),),
        )
