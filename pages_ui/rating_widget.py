import streamlit as st
from src.user_ratings import init_ratings_db, save_user_rating, get_user_rating, delete_user_rating, get_community_rating

def show_rating_widget(movie_id, username=None):
    """Hiển thị điểm cộng đồng và cho phép người dùng chấm/sửa/xóa điểm."""
    init_ratings_db()
    movie_id = int(movie_id)

    average, count = get_community_rating(movie_id)
    if count:
        st.write(f":star: **{average:.2f}/5** — {count:,} lượt đánh giá trên MovieMatch")
    else:
        st.caption("Chưa có người dùng MovieMatch đánh giá phim này.")

    flash_key = f"rating_flash_{movie_id}"
    flash_message = st.session_state.pop(flash_key, None)
    if flash_message:
        st.success(flash_message)

    if not username:
        st.info("Vui lòng đăng nhập để đánh giá phim.")
        return

    old_rating = get_user_rating(username, movie_id)
    if old_rating is not None:
        st.caption(f"Đánh giá hiện tại của bạn: :star: {old_rating:.1f}/5")

    options = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    rating = st.select_slider(
        "Chọn số sao",
        options=options,
        value=old_rating if old_rating is not None else 3.0,
        format_func=lambda value: f"{value:g} :star:",
        key=f"rating_{movie_id}",
    )

    col_save, col_delete = st.columns(2)
    with col_save:
        if st.button("Lưu đánh giá", key=f"save_rating_{movie_id}", width="stretch", type="primary"):
            try:
                save_user_rating(username, movie_id, rating)
                st.session_state[flash_key] = "Đã lưu đánh giá của bạn."
                st.rerun()
            except (TypeError, ValueError) as error:
                st.error(str(error))
            except Exception as error:
                st.error("Không thể lưu đánh giá. Vui lòng thử lại.")
                st.caption(str(error))

    with col_delete:
        if old_rating is not None and st.button("Xóa đánh giá", key=f"delete_rating_{movie_id}", width="stretch"):
            try:
                delete_user_rating(username, movie_id)
                st.session_state.pop(f"rating_{movie_id}", None)
                st.session_state[flash_key] = "Đã xóa đánh giá của bạn."
                st.rerun()
            except Exception as error:
                st.error("Không thể xóa đánh giá. Vui lòng thử lại.")
                st.caption(str(error))
