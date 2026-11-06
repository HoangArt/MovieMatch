# MovieMatch — Hệ thống gợi ý phim

MovieMatch là ứng dụng web xây dựng bằng **Python và Streamlit**, sử dụng bộ dữ liệu **MovieLens `ml-latest-small`** để khám phá dữ liệu phim và thử nghiệm nhiều phương pháp gợi ý. Người dùng có thể đăng ký tài khoản, chọn phim yêu thích, mở trang chi tiết phim, lưu điểm đánh giá cá nhân và so sánh các mô hình gợi ý.

> **Dữ liệu:** MovieLens `ml-latest-small` — khoảng 100 nghìn lượt đánh giá, 610 người dùng và 9.742 phim. Tải thông tin chính thức tại [GroupLens MovieLens](https://grouplens.org/datasets/movielens/).

## Nội dung

- [Tính năng](#tính-năng)
- [Công nghệ](#công-nghệ)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Cài đặt và chạy](#cài-đặt-và-chạy)
- [Cấu hình TMDB](#cấu-hình-tmdb)
- [Các mô hình gợi ý](#các-mô-hình-gợi-ý)
- [Cách sử dụng](#cách-sử-dụng)
- [Lưu trữ dữ liệu và mô hình](#lưu-trữ-dữ-liệu-và-mô-hình)
- [Giới hạn hiện tại và hướng phát triển](#giới-hạn-hiện-tại-và-hướng-phát-triển)
- [Khắc phục sự cố](#khắc-phục-sự-cố)

## Tính năng

- **Tài khoản người dùng:** đăng ký, đăng nhập và lưu thông tin tài khoản bằng SQLite.
- **Thiết lập sở thích ban đầu:** người dùng mới tìm, lọc và chọn các phim yêu thích; danh sách được lưu riêng theo tài khoản.
- **Trang chủ:** xem danh mục phim phổ biến, phim được đánh giá cao và phim thuộc các thể loại khác nhau.
- **Tìm kiếm phim:** tìm theo tên, lọc thể loại và sắp xếp kết quả.
- **Trang chi tiết phim:** xem poster, ảnh nền, mô tả, ngày phát hành/năm, thời lượng, thể loại và thông tin đánh giá nếu nguồn dữ liệu có sẵn.
- **Chấm điểm phim:** mỗi tài khoản có thể chấm từ 0,5 đến 5 sao với bước 0,5; có thể sửa hoặc xóa đánh giá của mình.
- **Gợi ý cá nhân hóa:** chọn mô hình để tạo danh sách phim gợi ý dựa trên sở thích và các điểm đã chấm.
- **Khám phá dữ liệu:** xem bảng phim, đánh giá, tags, links và dữ liệu đánh giá đã ghép.
- **Tải poster qua TMDB:** có cache và ảnh thay thế khi chưa có poster hoặc chưa cấu hình API key.

## Công nghệ

- Python
- Streamlit
- pandas, NumPy, SciPy
- scikit-learn
- TensorFlow/Keras (cho mô hình Embedding)
- SQLite (tài khoản, phim yêu thích, trạng thái onboarding và điểm do người dùng website chấm)
- TMDB API (poster, ảnh nền và thông tin phim bổ sung)

## Cấu trúc dự án

```text
MovieMatch/
├── main.py                         # Điểm khởi chạy và điều hướng trang
├── requirements.txt                # Các thư viện Python
├── README.md
├── .streamlit/
│   └── secrets.toml.example        # Mẫu cấu hình API key, không chứa key thật
├── data/
│   └── ml-latest-small/
│       ├── movies.csv              # Danh sách phim và thể loại
│       ├── ratings.csv             # Các lượt đánh giá của MovieLens
│       ├── tags.csv                # Tags do người dùng gán
│       ├── links.csv               # Ánh xạ movieId sang IMDb/TMDB ID
│       └── README.txt
├── pages_ui/
│   ├── auth.py                     # Đăng ký và đăng nhập
│   ├── data_explorer.py            # Khám phá các bảng dữ liệu
│   ├── favorite_movies.py          # Chọn và quản lý phim yêu thích
│   ├── home.py                     # Trang chủ
│   ├── movie_detail.py             # Chi tiết phim và đánh giá phim
│   ├── movie_display.py            # Tải/hiển thị poster dùng chung
│   ├── rated_movies.py             # Danh sách phim người dùng đã đánh giá
│   ├── rating_widget.py            # Widget đánh giá phim
│   ├── recommendations.py          # Giao diện gợi ý phim
│   └── search.py                   # Tìm kiếm phim
└── src/
    ├── common.py                  # Thành phần hiển thị và hàm dùng chung
    ├── content_recommender.py     # TF-IDF và cosine similarity
    ├── database.py                # SQLite và thao tác dữ liệu tài khoản
    ├── recommender_models.py      # User/Item KNN, SVD và Keras Embedding
    ├── tmdb.py                    # Thông tin chi tiết phim từ TMDB và tải poster theo lô
    └── user_ratings.py            # Lưu và truy xuất điểm đánh giá của người dùng website
```

## Cài đặt và chạy

### 1. Yêu cầu

- Python 3.14.6 và `pip`.
- Kết nối Internet lần đầu nếu cần tải dữ liệu MovieLens hoặc gọi TMDB.
- TensorFlow cần môi trường Python được phiên bản TensorFlow đang cài hỗ trợ. Xem [hướng dẫn cài TensorFlow chính thức](https://www.tensorflow.org/install/pip). Trên Windows, phiên bản TensorFlow cài bằng pip thông thường chạy trên CPU; cấu hình GPU có yêu cầu riêng.

### 2. Mở thư mục dự án

Mở terminal tại thư mục gốc `MovieMatch/` — nơi có file `main.py` và `requirements.txt`.

### 3. Tạo môi trường ảo

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 4. Cài thư viện

```bash
pip install -r requirements.txt
```

### 5. Chạy ứng dụng

```bash
streamlit run main.py
```

Streamlit sẽ hiển thị địa chỉ chạy local trong terminal (thường là `http://localhost:8501`). Mở địa chỉ đó trong trình duyệt.

### 6. Dữ liệu MovieLens

Bốn tệp CSV của `ml-latest-small` được đặt tại `data/ml-latest-small/`. Nếu thiếu các tệp cần thiết, `src/common.py` có thể tải bộ dữ liệu từ GroupLens; thao tác này cần kết nối Internet.

## Cấu hình TMDB

TMDB được dùng để tải poster, ảnh nền và thông tin chi tiết cho các phim có `tmdbId` tương ứng trong `links.csv`. Ứng dụng vẫn có thể hiển thị dữ liệu MovieLens nếu chưa cấu hình key, nhưng poster hoặc mô tả lấy từ TMDB có thể không xuất hiện.

1. Tạo API key trong tài khoản [The Movie Database (TMDB)](https://www.themoviedb.org/).
2. Sao chép file mẫu thành file secrets riêng.

**Windows PowerShell:**

```powershell
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
```

3. Mở `.streamlit/secrets.toml` và thay giá trị mẫu:

```toml
TMDB_API_KEY = "YOUR_TMDB_API_KEY"
```

Có thể dùng biến môi trường `TMDB_API_KEY` thay cho Streamlit Secrets.

## Các mô hình gợi ý

Notebook huấn luyện/đánh giá đầy đủ các mô hình cần `tensorflow`; cài trong môi trường notebook bằng `%pip install tensorflow` nếu chưa có. Trong ứng dụng Streamlit, TensorFlow là tùy chọn và chỉ cần cho Keras Embedding.

Trên trang **Gợi ý phim**, người dùng có thể chọn một trong các phương pháp sau:

### 1. Content-based — TF-IDF + cosine similarity

- Mã nguồn: `src/content_recommender.py`.
- Dùng tên phim, thể loại và tags để tạo vector TF-IDF.
- Tạo hồ sơ bằng cách kết hợp vector của các phim yêu thích, sau đó xếp hạng phim theo cosine similarity.
- Phù hợp với người dùng mới chưa có lịch sử đánh giá trên website (*cold-start*).

### 2. User-based KNN

- Mã nguồn: `src/recommender_models.py`.
- Tìm những người dùng MovieLens có mẫu đánh giá gần với hồ sơ điểm của tài khoản hiện tại.
- Đề xuất các phim được những láng giềng này đánh giá tích cực (mặc định từ 4/5), xếp hạng theo tỷ lệ phiếu tích cực có trọng số cosine similarity.
- `recommendation_score` là điểm xếp hạng từ 0 đến 1, **không phải rating dự đoán**; KNN được đánh giá bằng Precision@K/Recall@K, không đưa vào RMSE.

### 3. Item-based KNN

- Mã nguồn: `src/recommender_models.py`.
- Tìm các phim có mẫu đánh giá tương tự những phim người dùng đã thích (rating từ 4/5 trở lên).
- Xếp hạng phim chưa xem theo cosine similarity có trọng số với các phim yêu thích; không ước lượng rating cho phim ứng viên.
- `recommendation_score` là điểm tương đồng dùng để sắp xếp danh sách, không phải rating dự đoán; KNN được đánh giá bằng Precision@K/Recall@K, không đưa vào RMSE.

### 4. Truncated SVD

- Mã nguồn: `src/recommender_models.py`.
- Phân rã ma trận đánh giá thành các nhân tố ẩn. Với tài khoản website mới, hệ thống suy ra vector người dùng từ các phim đã được đánh giá.

### 5. Keras Embedding

- Mã nguồn: `src/recommender_models.py`.
- Huấn luyện lớp embedding cho người dùng và phim cùng các bias để dự đoán điểm đánh giá từ dữ liệu MovieLens.
- Mô hình này cần TensorFlow và chỉ huấn luyện khi người dùng chọn; có thể mất thêm thời gian ở lần sử dụng đầu tiên. Cài phần phụ thuộc tùy chọn bằng `pip install -r requirements-optional-keras.txt`.

**Cách kết hợp dữ liệu:** các mô hình cộng tác được xây dựng từ lịch sử đánh giá MovieLens. Điểm đánh giá do tài khoản CinaMatch tạo ra được lưu riêng theo tài khoản, sau đó dùng làm hồ sơ để xếp hạng phim. `user_id` của website không được xem là `userId` trong MovieLens.

## Cách sử dụng

1. Mở ứng dụng và đăng ký tài khoản mới.
2. Chọn các phim yêu thích theo hướng dẫn onboarding rồi lưu lựa chọn.
3. Vào **Gợi ý phim** và chọn mô hình muốn thử.
4. Mở trang chi tiết từ các thẻ phim, xem thông tin và chấm điểm phim.
5. Quay lại **Gợi ý phim**, chọn Content-based, User-based KNN, Item-based KNN, Truncated SVD hoặc Keras Embedding để tạo danh sách dựa trên hồ sơ đã cập nhật. Các mô hình cộng tác cần ít nhất 3 rating đã lưu; nếu chưa đủ, hệ thống dùng TF-IDF cho cold-start. Với KNN, giao diện hiển thị điểm ủng hộ/độ tương đồng để xếp hạng phim; chỉ SVD và Keras Embedding hiển thị rating dự đoán.
6. Vào **Phim yêu thích** để quản lý danh sách yêu thích, **Phim đã đánh giá** để xem các phim và điểm bạn đã chấm (tải poster theo từng lô), hoặc mở **Thống kê** để xem dữ liệu MovieLens.

## Lưu trữ dữ liệu và mô hình

- **SQLite:** `src/database.py` tạo `movie_recommendations.db` tại thư mục gốc của project khi ứng dụng chạy lần đầu. Database lưu tài khoản, danh sách yêu thích, trạng thái onboarding và điểm đánh giá của người dùng website.
- **Bảo vệ mật khẩu:** ứng dụng lưu salt và giá trị băm PBKDF2-HMAC-SHA256, không lưu mật khẩu thuần văn bản.
- **Dữ liệu MovieLens:** nằm trong `data/ml-latest-small/`.
- **Cache mô hình:** ma trận TF-IDF và các mô hình cộng tác MovieLens (User/Item KNN, Truncated SVD) được cache trong bộ nhớ tiến trình Streamlit bằng `st.cache_resource`; Keras Embedding chỉ được huấn luyện khi chọn mô hình và TensorFlow đã cài. Ứng dụng không tự ghi các mô hình này thành file `.joblib`, `.pkl` hoặc `.keras`; sau khi cache bị xóa hoặc ứng dụng khởi động lại, chúng có thể được xây dựng/huấn luyện lại.
- **TMDB:** dữ liệu trả về được cache để giảm các yêu cầu lặp lại.

Không xóa `movie_recommendations.db` nếu cần giữ tài khoản và đánh giá đã lưu. Khi sao lưu hoặc triển khai, bảo vệ database và secrets như dữ liệu riêng tư.

## Giới hạn hiện tại và hướng phát triển

- Ứng dụng hiện dùng SQLite để làm demo cục bộ. Muốn triển khai cloud phục vụ nhiều người dùng ổn định, nên chuyển dữ liệu tài khoản và tương tác sang một database được quản lý, có lưu trữ bền vững (ví dụ PostgreSQL/Supabase), đồng thời cấu hình quyền truy cập và backup.
- Notebook đánh giá offline bằng **Precision@K và Recall@K** cho TF-IDF, User-based KNN, Item-based KNN, SVD và Keras Embedding. **RMSE chỉ dùng cho Surprise SVD, Truncated SVD và Keras Embedding**, là các mô hình dự đoán rating. Báo cáo hiện được lưu ở các tệp CSV trong thư mục `results/` khi chạy notebook; chưa tích hợp thành trang đánh giá hoàn chỉnh trong ứng dụng.
- Nên lưu các mô hình đã huấn luyện thành artifact có phiên bản nếu muốn giảm thời gian khởi động lại và triển khai production.
- Keras Embedding cần được chạy kiểm thử trên môi trường có TensorFlow; lần chạy đầu tiên sẽ huấn luyện mô hình và có thể chậm hơn các mô hình khác.

## Khắc phục sự cố

### Không tải được poster hoặc mô tả

- Kiểm tra `TMDB_API_KEY` trong `.streamlit/secrets.toml` hoặc biến môi trường.
- Kiểm tra `tmdbId` trong `data/ml-latest-small/links.csv`.
- Nếu không có poster trên TMDB, ứng dụng sẽ hiển thị phần ảnh thay thế.

### Không tìm thấy dữ liệu MovieLens

- Chạy ứng dụng từ thư mục gốc `MovieMatch/`.
- Kiểm tra các tệp `movies.csv`, `ratings.csv`, `tags.csv`, `links.csv` trong `data/ml-latest-small/`.
- Nếu ứng dụng cần tải dữ liệu, kiểm tra kết nối Internet.

### Lỗi khi cài/chạy Keras Embedding

- Xác nhận môi trường ảo đã được kích hoạt.
- Cài thư viện theo `requirements.txt` và kiểm tra phiên bản Python được TensorFlow hỗ trợ.
- Có thể kiểm tra cài đặt bằng lệnh:

```bash
python -c "import tensorflow as tf; print(tf.__version__)"
```

### Tài khoản không đăng nhập được sau khi đổi môi trường

- Xác nhận bạn đang dùng đúng thư mục project và đúng file `movie_recommendations.db`.
- Tránh xóa hoặc tạo database mới nếu cần giữ tài khoản cũ.

---
