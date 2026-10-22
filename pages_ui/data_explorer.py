import streamlit as st

# Import hàm load dữ liệu từ file src/data.py
from src.data import load_movielens_data

# Cache dữ liệu để tránh tải lại nhiều lần


@st.cache_data(show_spinner="Đang tải dữ liệu và đọc dữ liệu Movielens...")
def get_data():
    return load_movielens_data()

# Hàm hiển thị trang


def show_data_explorer_page():
    st.header("Khám phá dữ liệu Movielens")
    st.write("Dưới đây là dữ liệu Movielens được tải từ các tệp CSV.")
    st.write(
        "Tại đây, bạn có thể xem danh sách phim, "
        "đánh giá và dữ liệu sau khi ghép."
    )

    try:
        movies, ratings, tags, links, ratings_with_movies = get_data()

    except Exception as e:
        st.error("Không thể tải hoặc đọc dữ liệu MovieLens.")
        st.code(str(e))
        st.info(
            "Kiểm tra kết nối Internet hoặc bảo đảm các file CSV "
            "nằm trong data/ml-latest-small/."
        )
        return

    # Hiển thị dữ liệu
    st.subheader("Tổng quan dữ liệu")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Số người dùng",
        f"{ratings['userId'].nunique():,}"
    )

    col2.metric(
        "Số phim",
        f"{movies['movieId'].nunique():,}"
    )

    col3.metric(
        "Số lượt đánh giá",
        f"{len(ratings):,}"
    )

    col4.metric(
        "Điểm trung bình",
        f"{ratings['rating'].mean():.2f} / 5"
    )

    # 7. Tạo các tab để xem từng loại dữ liệu
    tab_movies, tab_ratings, tab_merged, tab_tags, tab_links = (
        st.tabs([
            "Danh sách phim",
            "Đánh giá",
            "Dữ liệu đã ghép",
            "Tags",
            "Links"
        ])
    )

    # 8. Tab danh sách phim
    with tab_movies:
        st.subheader("Danh sách phim")

        search_text = st.text_input(
            "Tìm phim theo tên",
            placeholder="Ví dụ: Toy Story"
        )

        if search_text:
            filtered_movies = movies[
                movies["title"].str.contains(
                    search_text,
                    case=False,
                    na=False,
                    regex=False
                )
            ]
        else:
            filtered_movies = movies

        st.caption(
            f"Tìm thấy {len(filtered_movies):,} phim."
            " Bảng bên dưới hiển thị tối đa 100 dòng."
        )

        st.dataframe(
            filtered_movies.head(100),
            use_container_width=True,
            hide_index=True
        )

    # 9. Tab đánh giá
    with tab_ratings:
        st.subheader("Các lượt đánh giá")

        st.write(
            "Mỗi dòng thể hiện một người dùng "
            "đánh giá một bộ phim."
        )

        st.dataframe(
            ratings.head(100),
            use_container_width=True,
            hide_index=True
        )

    # 10. Tab dữ liệu đã ghép
    with tab_merged:
        st.subheader("Đánh giá kèm thông tin phim")

        st.write(
            "Bảng này kết hợp điểm đánh giá "
            "với tên và thể loại của phim."
        )

        st.dataframe(
            ratings_with_movies.head(100),
            use_container_width=True,
            hide_index=True
        )

    # 11. Tab tags
    with tab_tags:
        st.subheader("Thẻ mô tả phim")

        st.dataframe(
            tags.head(100),
            use_container_width=True,
            hide_index=True
        )

    # 12. Tab links
    with tab_links:
        st.subheader("Liên kết phim")

        st.dataframe(
            links.head(100),
            use_container_width=True,
            hide_index=True
        )
