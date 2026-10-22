import streamlit as st
import pandas as pd

from pages_ui.common import context, enrich, format_movie_title, translate_genres
from src.database import (
    delete_user_movie_rating,
    get_user_movie_ratings,
    save_user_movie_rating,
)
from src.tmdb import get_movie_info


def preload_movie_detail(movie_id):
    """Tải trước dữ liệu TMDB của phim để có thể dùng cùng transition overlay."""
    movies, _, _ = context()
    selected = movies[movies["movieId"] == int(movie_id)]
    if selected.empty:
        return {}
    tmdb_id = selected.iloc[0].get("tmdbId")
    if pd.isna(tmdb_id):
        return {}
    try:
        return get_movie_info(int(float(tmdb_id)), language="vi-VN")
    except (TypeError, ValueError, OverflowError):
        return {}


def _return_to_previous_page():
    target_page = st.session_state.get("return_page", "Trang chủ")
    if target_page == "Chi tiết phim":
        target_page = "Trang chủ"
    # Trong onboarding, main.py tự quay lại trang thiết lập sở thích; trang này
    # không phải một lựa chọn của radio sidebar.
    if target_page != "Thiết lập sở thích":
        st.session_state["main_navigation"] = target_page
    st.session_state.pop("page", None)
    st.session_state.pop("detail_loaded_movie_id", None)


def show_movie_detail_page(user_id):
    """Hiển thị thông tin TMDB/MovieLens và cho phép lưu đánh giá phim."""
    movie_id = st.session_state.get("selected_movie")
    if movie_id is None:
        st.info("Bạn chưa chọn phim. Hãy quay lại danh sách phim.")
        st.button("← Quay lại", on_click=_return_to_previous_page)
        return

    movies, ratings, _ = context()
    movie_data = enrich(movies, ratings)
    selected = movie_data[movie_data["movieId"] == int(movie_id)]
    if selected.empty:
        st.error("Không tìm thấy phim trong dữ liệu MovieLens.")
        st.button("← Quay lại", on_click=_return_to_previous_page)
        return

    movie = selected.iloc[0]
    tmdb_info = preload_movie_detail(int(movie_id))
    user_ratings = get_user_movie_ratings(user_id)
    current_rating = user_ratings.get(int(movie_id))

    st.button("← Quay lại", on_click=_return_to_previous_page)
    title = format_movie_title(movie["title"])
    st.title(title)
    if tmdb_info.get("tagline"):
        st.caption(f"*{tmdb_info['tagline']}*")

    backdrop = tmdb_info.get("backdrop")
    if backdrop:
        st.image(backdrop, use_container_width=True)

    poster_col, info_col = st.columns([1, 2], gap="large")
    with poster_col:
        poster = tmdb_info.get("poster")
        if poster:
            st.image(poster, use_container_width=True)
        else:
            st.markdown(
                """
                <div style="aspect-ratio:2/3; display:flex; align-items:center; 
                justify-content:center; border-radius:12px; background:#202027; 
                color:#aaa; font-size:48px;">🎬</div>
                """,
                unsafe_allow_html=True,
            )

    with info_col:
        genres = translate_genres(movie.get("genres", ""))
        st.markdown(f"**Thể loại:** {genres}")

        release_date = tmdb_info.get("release_date") or ""
        year = release_date[:4] if len(release_date) >= 4 else ""
        if not year:
            year_match = pd.Series([str(movie["title"])]).str.extract(r"\((\d{4})\)\s*$").iloc[0, 0]
            year = str(year_match) if pd.notna(year_match) else "Chưa rõ"
        st.write(f"**Năm phát hành:** {year}")

        runtime = tmdb_info.get("runtime")
        if runtime:
            st.write(f"**Thời lượng:** {int(runtime)} phút")
        if tmdb_info.get("original_language"):
            st.write(f"**Ngôn ngữ gốc:** {tmdb_info['original_language'].upper()}")
        if tmdb_info.get("status"):
            st.write(f"**Trạng thái:** {tmdb_info['status']}")

        metric1, metric2 = st.columns(2)
        mean_rating = movie.get("mean")
        rating_count = int(movie.get("count", 0))
        metric1.metric(
            "Điểm MovieLens",
            f"{float(mean_rating):.2f}/5" if pd.notna(mean_rating) else "Chưa có",
        )
        metric2.metric("Lượt đánh giá", f"{rating_count:,}")

        tmdb_vote = tmdb_info.get("vote_average")
        if tmdb_vote is not None:
            st.caption(f"Điểm TMDB: {float(tmdb_vote):.1f}/10")
        if tmdb_info.get("homepage"):
            st.link_button("Trang web chính thức", tmdb_info["homepage"])

    st.subheader("Nội dung phim")
    overview = tmdb_info.get("overview", "")
    if not overview:
        tmdb_id = movie.get("tmdbId")
        if pd.notna(tmdb_id):
            english_info = get_movie_info(int(float(tmdb_id)), language="en-US")
            overview = english_info.get("overview", "")
    st.write(overview or "TMDB chưa cung cấp phần mô tả cho bộ phim này.")

    st.divider()
    st.subheader("⭐ Đánh giá phim")
    st.write(
        "Điểm đánh giá được lưu riêng cho tài khoản của bạn và có thể được dùng "
        "để cá nhân hóa các mô hình gợi ý KNN, SVD và Keras Embedding."
    )
    if current_rating is None:
        default_rating = 3.0
        st.caption("Bạn chưa đánh giá phim này.")
    else:
        default_rating = float(current_rating)
        st.success(f"Đánh giá hiện tại của bạn: {current_rating:.1f}/5")

    rating_key = f"detail_rating_{user_id}_{int(movie_id)}"
    rating_value = st.slider(
        "Chọn điểm số",
        min_value=0.5,
        max_value=5.0,
        value=default_rating,
        step=0.5,
        key=rating_key,
    )
    save_col, delete_col = st.columns([2, 1])
    with save_col:
        if st.button("Lưu đánh giá", type="primary", use_container_width=True):
            save_user_movie_rating(user_id, int(movie_id), float(rating_value))
            st.session_state["detail_rating_saved"] = True
            st.rerun()
    with delete_col:
        if current_rating is not None and st.button("Xóa đánh giá", use_container_width=True):
            delete_user_movie_rating(user_id, int(movie_id))
            st.session_state["detail_rating_deleted"] = True
            st.rerun()

    if st.session_state.pop("detail_rating_saved", False):
        st.success("Đã lưu đánh giá. Gợi ý sẽ sử dụng điểm số mới của bạn.")
    if st.session_state.pop("detail_rating_deleted", False):
        st.info("Đã xóa đánh giá của bạn cho phim này.")
