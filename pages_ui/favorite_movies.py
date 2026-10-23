import pandas as pd
import streamlit as st
from src.common import context, enrich, GENRE_TRANSLATIONS, translate_genres, shorten_text
from pages_ui.movie_display import load_poster_data, show_movie_poster
from src.database import get_user_favorite_movie_ids, mark_onboarding_completed, save_user_favorite_movies

MIN_FAVORITES = 3
RESULT_LIMIT = 24

def _toggle_movie(selection_key, movie_id):
    """Thêm/bỏ movieId trong danh sách lựa chọn tạm ở session."""
    selected = list(st.session_state.get(selection_key, []))
    movie_id = int(movie_id)
    if movie_id in selected:
        selected = [value for value in selected if int(value) != movie_id]
    else:
        selected.append(movie_id)
    st.session_state[selection_key] = selected


def show_favorite_movies_page(user_id, first_time=False):
    """Trang onboarding cho người mới và trang chỉnh sửa phim yêu thích."""
    movies, ratings, _ = context()
    movie_data = enrich(movies, ratings)

    selection_key = f"favorite_selection_user_{int(user_id)}"
    if selection_key not in st.session_state:
        st.session_state[selection_key] = get_user_favorite_movie_ids(user_id)

    selected_ids = [int(movie_id)
                    for movie_id in st.session_state[selection_key]]
    selected_set = set(selected_ids)

    if first_time:
        st.title("Chọn những bộ phim bạn yêu thích")
        st.write(
            "Hãy chọn ít nhất 3 phim bạn đã xem và yêu thích. "
            "Hệ thống sẽ phân tích tên phim, thể loại và tags để tìm các phim tương tự, "
            "ngay cả khi tài khoản của bạn chưa có lịch sử chấm điểm."
        )
        st.caption("Lựa chọn được lưu riêng theo tài khoản của bạn.")
    else:
        st.title("Phim yêu thích của tôi")
        st.write(
            "Thêm hoặc bỏ phim để cập nhật hồ sơ sở thích. "
            "Các thay đổi chỉ được lưu khi bạn nhấn nút lưu ở cuối trang."
        )

    # Hiển thị các phim đã chọn và cho phép gỡ ngay cả khi đã lọc danh sách.
    st.subheader(f"Đã chọn {len(selected_ids)} phim")
    if selected_ids:
        selected_data = movie_data[movie_data["movieId"].isin(
            selected_set)].copy()

        # Đảm bảo dữ liệu phim có tmdbId để tải poster.
        if ("tmdbId" not in selected_data.columns and {"movieId", "tmdbId"}.issubset(movies.columns)):
            selected_data = selected_data.merge(movies[["movieId", "tmdbId"]].drop_duplicates(
                subset=["movieId"]), on="movieId", how="left")

        # Chỉ tải poster của những phim đã chọn.
        selected_posters = load_poster_data(
            selected_data, spinner_text="Đang tải poster phim yêu thích...")

        with st.expander("Xem danh sách phim đã chọn", expanded=True):
            for _, movie in selected_data.iterrows():
                poster_col, info_col, action_col = st.columns([1, 7, 1.5])

                # Poster nằm bên trái
                with poster_col:
                    show_movie_poster(movie, selected_posters, width=65)

                # Tên phim và thể loại nằm bên cạnh poster
                with info_col:
                    st.write(f"**{movie['title']}**")
                    st.caption(translate_genres(movie["genres"]))

                # Nút bỏ chọn nằm bên phải.
                with action_col:
                    if st.button("Bỏ chọn",
                                 key=(f"remove_favorite_{user_id}_"
                                      f"{int(movie['movieId'])}"), width="stretch"):
                        _toggle_movie(selection_key, int(movie["movieId"]))
                        st.rerun()

    else:
        st.info("Bạn chưa chọn phim nào. Hãy tìm và chọn vài phim bên dưới.")

    st.divider()
    st.subheader("Khám phá và chọn phim")

    search_col, genre_col = st.columns([2, 1])
    with search_col:
        query = st.text_input(
            "Tìm theo tên phim",
            placeholder="Ví dụ: Toy Story, The Matrix, Titanic...",
            key=f"favorite_search_{user_id}",
        )
    genre_values = sorted({
        genre
        for genre_string in movie_data["genres"].dropna().astype(str)
        for genre in genre_string.split("|")
        if genre and genre != "(no genres listed)"
    })
    with genre_col:
        selected_genre = st.selectbox(
            "Lọc thể loại",
            options=["Tất cả"] + genre_values,
            format_func=lambda value: (
                "Tất cả thể loại"
                if value == "Tất cả"
                else GENRE_TRANSLATIONS.get(value, value)
            ),
            key=f"favorite_genre_{user_id}",
        )

    filtered = movie_data.copy()
    if query.strip():
        filtered = filtered[
            filtered["title"].str.contains(
                query.strip(), case=False, regex=False, na=False
            )
        ]
    if selected_genre != "Tất cả":
        filtered = filtered[
            filtered["genres"].fillna("").str.split("|").apply(
                lambda values: selected_genre in values
            )
        ]

    # Khi chưa tìm kiếm, ưu tiên phim phổ biến; khi có kết quả tìm kiếm,
    # vẫn ưu tiên phim được đánh giá tốt và có nhiều lượt đánh giá.
    filtered = filtered.sort_values(
        by=["count", "score", "title"],
        ascending=[False, False, True],
    )

    st.caption(
        f"Tìm thấy {len(filtered):,} phim. "
        f"Hiển thị tối đa {RESULT_LIMIT} phim mỗi lần; hãy nhập thêm tên phim "
        "hoặc chọn thể loại để thu hẹp kết quả."
    )
    displayed = filtered.head(RESULT_LIMIT)

    if displayed.empty:
        st.warning("Không tìm thấy phim phù hợp. Hãy thử từ khóa khác.")
    else:
        # Đảm bảo displayed có tmdbId để tìm poster
        if "tmdbId" not in displayed.columns:
            if {"movieId", "tmdbId"}.issubset(movies.columns):
                displayed = displayed.merge(movies[["movieId", "tmdbId"]].drop_duplicates(
                    subset=["movieId"]), on="movieId", how="left")

        # Chỉ tải poster của tối đa 24 phim đang hiển thị.
        poster = load_poster_data(
            displayed, spinner_text="Đang tải poster cho các phim...")

        columns = st.columns(3)
        for index, (_, movie) in enumerate(displayed.iterrows()):
            movie_id = int(movie["movieId"])
            with columns[index % 3]:
                with st.container(border=True):
                    show_movie_poster(movie, poster, width="content")

                    st.write(f"**{shorten_text((movie['title']), max_chars=40)}**")
                    st.caption(shorten_text(translate_genres(movie["genres"]), max_chars=50))
                    avg_rating = movie.get("mean")
                    rating_count = int(movie.get("count", 0))
                    if pd.notna(avg_rating) and rating_count > 0:
                        st.caption(
                            f"{float(avg_rating):.1f}/5 · {rating_count:,} lượt đánh giá")
                    else:
                        st.caption("Chưa có đánh giá từ MovieLens")

                    is_selected = movie_id in selected_set
                    button_label = "✓ Đã chọn · Bỏ chọn" if is_selected else "+ Thêm vào yêu thích"
                    if st.button(
                        button_label,
                        key=f"toggle_favorite_{user_id}_{movie_id}",
                        width="stretch",
                    ):
                        _toggle_movie(selection_key, movie_id)
                        st.rerun()

    st.divider()
    current_selection = [int(movie_id)
                         for movie_id in st.session_state[selection_key]]
    save_col, skip_col = st.columns([3, 1])
    with save_col:
        st.button(
            "Lưu sở thích và xem gợi ý",
            key=f"save_favorite_movies_{user_id}",
            type="primary",
            width="stretch",
            disabled=len(current_selection) < MIN_FAVORITES,
            on_click=_save_favorites,
            args=(int(user_id), selection_key),
        )
        if len(current_selection) < MIN_FAVORITES:
            st.caption(
                f"Chọn thêm {MIN_FAVORITES - len(current_selection)} phim để bật gợi ý cá nhân hóa.")
    with skip_col:
        if first_time and st.button(
            "Để sau",
            key=f"skip_favorite_setup_{user_id}",
            width="stretch",
        ):
            # Bỏ các lựa chọn chưa lưu trong session; giữ lại dữ liệu đã có trong DB.
            st.session_state[selection_key] = get_user_favorite_movie_ids(
                user_id)
            mark_onboarding_completed(user_id)
            st.session_state["main_navigation"] = "Gợi ý phim"
            st.rerun()


def _save_favorites(user_id, selection_key):
    """
    Lưu danh sách phim yêu thích đã chọn và chuyển đến trang 'Gợi ý phim'
    """
    selected_ids = st.session_state.get(selection_key, [])
    if len(set(int(value) for value in selected_ids)) < MIN_FAVORITES:
        return
    save_user_favorite_movies(user_id, selected_ids)
    st.session_state["main_navigation"] = "Gợi ý phim"
