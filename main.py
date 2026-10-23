import streamlit as st
from pages_ui.home import show_home_page
from pages_ui.search import show_search
from pages_ui.auth import show_auth_page
from pages_ui.data_explorer import show_data_explorer_page
from pages_ui.favorite_movies import show_favorite_movies_page
from pages_ui.recommendations import show_recommendations_page
from pages_ui.movie_detail import show_movie_detail_page
from src.database import init_db, is_onboarding_completed

# Cấu hình trang web
st.set_page_config(
    page_title="MovieMatch",
    page_icon=":popcorn:",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.user_id is None:
    show_auth_page()

elif "movie_id" in st.query_params:
    # Đang mở trang chi tiết phim
    try:
        movie_id = int(st.query_params["movie_id"])

        if movie_id <= 0:
            raise ValueError("movie_id phải là số dương")

        show_movie_detail_page(movie_id)

    except (ValueError, TypeError):
        st.error("Đường dẫn phim không hợp lệ.")

        if st.button("Quay lại trang chủ"):
            st.query_params.clear()
            st.rerun()

else:
    # Tạo thanh bên
    st.sidebar.title("MovieMatch")
    st.sidebar.caption("Khám phá thế giới điện ảnh")
    st.sidebar.divider()
    st.sidebar.write(f"Xin chào, **{st.session_state.username}**!")

    if not is_onboarding_completed(st.session_state.user_id):
        st.sidebar.info("Bước đầu tiên: Chọn phim yêu thích")

        show_favorite_movies_page(
            user_id=st.session_state.user_id, first_time=True)

    else:
        # Tạo các tùy chọn trong thanh bên
        page = st.sidebar.radio(
            "Chọn một trang:",
            [
                "Trang chủ",
                "Tìm kiếm",
                "Gợi ý phim",
                "Phim yêu thích",
                "Đăng nhập/Đăng ký",
                "Thống kê"
            ],
            key="main_navigation"
        )

        # Hiển thị nội dung dựa trên lựa chọn của người dùng
        if page == "Trang chủ":
            show_home_page()

        elif page == "Tìm kiếm":
            show_search()

        elif page == "Gợi ý phim":
            show_recommendations_page(st.session_state.user_id)

        elif page == "Phim yêu thích":
            show_favorite_movies_page(
                user_id=st.session_state.user_id, first_time=False)

        elif page == "Đăng nhập/Đăng ký":
            show_auth_page()

        elif page == "Thống kê":
            show_data_explorer_page()

    if st.sidebar.button("Đăng xuất"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()
