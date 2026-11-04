import pandas as pd
import streamlit as st

from src.common import (
    context,
    enrich,
    GENRE_TRANSLATIONS,
    translate_genres,
    shorten_text,
)

from pages_ui.movie_display import (
    load_poster_data,
    show_movie_poster,
)

from src.database import (
    get_user_favorite_movie_ids,
    mark_onboarding_completed,
    save_user_favorite_movies,
)


MIN_FAVORITES = 3
RESULT_LIMIT = 24


# ==========================================
# 1. CHỌN HOẶC BỎ CHỌN PHIM
# ==========================================

def _toggle_movie(selection_key, movie_id):
    selected = list(st.session_state.get(selection_key, []))
    movie_id = int(movie_id)

    if movie_id in selected:
        selected.remove(movie_id)
    else:
        selected.append(movie_id)

    st.session_state[selection_key] = selected


# ==========================================
# 2. LƯU PHIM VÀ CHUYỂN TRANG
# ==========================================

def _save_favorites(user_id, selection_key):
    selected = st.session_state.get(selection_key, [])

    if len(set(map(int, selected))) < MIN_FAVORITES:
        return

    save_user_favorite_movies(user_id, selected)

    # Chuyển đến trang gợi ý
    st.session_state["main_navigation"] = "Gợi ý phim"

    # Yêu cầu cuộn lên đầu trang
    st.session_state["scroll_to_top"] = True


# ==========================================
# 3. TRANG PHIM YÊU THÍCH
# ==========================================

def show_favorite_movies_page(user_id, first_time=False):

    movies, ratings, _ = context()
    movie_data = enrich(movies, ratings)

    # Bổ sung tmdbId nếu chưa có
    if "tmdbId" not in movie_data.columns:
        movie_data = movie_data.merge(
            movies[["movieId", "tmdbId"]],
            on="movieId",
            how="left",
        )

    selection_key = f"favorite_selection_user_{int(user_id)}"

    if selection_key not in st.session_state:
        st.session_state[selection_key] = (
            get_user_favorite_movie_ids(user_id)
        )

    selected_ids = [
        int(x) for x in st.session_state[selection_key]
    ]

    selected_set = set(selected_ids)

    # ======================================
    # TIÊU ĐỀ
    # ======================================

    if first_time:
        st.title("Chọn những bộ phim bạn yêu thích")
        st.write(
            "Hãy chọn ít nhất 3 phim để MovieMatch "
            "đưa ra gợi ý phù hợp với sở thích của bạn."
        )
    else:
        st.title("Phim yêu thích của tôi")
        st.write(
            "Thêm hoặc bỏ phim yêu thích, sau đó "
            "nhấn lưu để cập nhật gợi ý."
        )

    # ======================================
    # DANH SÁCH PHIM ĐÃ CHỌN
    # ======================================

    st.subheader(f"Đã chọn {len(selected_ids)} phim")

    if selected_ids:

        selected_data = movie_data[
            movie_data["movieId"].isin(selected_set)
        ]

        posters = load_poster_data(selected_data)

        with st.expander(
            "Xem danh sách phim đã chọn",
            expanded=True,
        ):

            for _, movie in selected_data.iterrows():

                col1, col2, col3 = st.columns([1, 7, 1.5])

                with col1:
                    show_movie_poster(
                        movie, posters, width=65
                    )

                with col2:
                    st.write(f"**{movie['title']}**")
                    st.caption(
                        translate_genres(movie["genres"])
                    )

                with col3:
                    if st.button(
                        "Bỏ chọn",
                        key=f"remove_{user_id}_{movie['movieId']}",
                        width="stretch",
                    ):
                        _toggle_movie(
                            selection_key,
                            movie["movieId"],
                        )
                        st.rerun()

    else:
        st.info("Bạn chưa chọn phim nào.")

    # ======================================
    # TÌM KIẾM VÀ LỌC PHIM
    # ======================================

    st.divider()
    st.subheader("Khám phá và chọn phim")

    col1, col2 = st.columns([2, 1])

    with col1:
        query = st.text_input(
            "Tìm theo tên phim",
            placeholder="Ví dụ: Titanic, The Matrix...",
            key=f"favorite_search_{user_id}",
        )

    genres = sorted({
        genre
        for value in movie_data["genres"].dropna()
        for genre in str(value).split("|")
        if genre and genre != "(no genres listed)"
    })

    with col2:
        selected_genre = st.selectbox(
            "Lọc thể loại",
            ["Tất cả"] + genres,
            format_func=lambda x: (
                "Tất cả thể loại"
                if x == "Tất cả"
                else GENRE_TRANSLATIONS.get(x, x)
            ),
            key=f"favorite_genre_{user_id}",
        )

    filtered = movie_data.copy()

    if query.strip():
        filtered = filtered[
            filtered["title"].str.contains(
                query.strip(),
                case=False,
                regex=False,
                na=False,
            )
        ]

    if selected_genre != "Tất cả":
        filtered = filtered[
            filtered["genres"]
            .fillna("")
            .str.split("|")
            .apply(lambda x: selected_genre in x)
        ]

    filtered = filtered.sort_values(
        ["count", "score", "title"],
        ascending=[False, False, True],
    )

    displayed = filtered.head(RESULT_LIMIT)

    st.caption(
        f"Tìm thấy {len(filtered):,} phim. "
        f"Đang hiển thị {len(displayed)} phim."
    )

    # ======================================
    # HIỂN THỊ PHIM
    # ======================================

    if displayed.empty:
        st.warning("Không tìm thấy phim phù hợp.")

    else:
        posters = load_poster_data(displayed)
        columns = st.columns(3)

        for index, (_, movie) in enumerate(
            displayed.iterrows()
        ):

            movie_id = int(movie["movieId"])

            with columns[index % 3]:
                with st.container(border=True):

                    show_movie_poster(
                        movie, posters, width="content"
                    )

                    st.write(
                        f"**{shorten_text(movie['title'], max_chars=40)}**"
                    )

                    st.caption(
                        shorten_text(
                            translate_genres(movie["genres"]),
                            max_chars=50,
                        )
                    )

                    rating = movie.get("mean")
                    count = movie.get("count", 0)

                    count = (
                        int(count)
                        if pd.notna(count)
                        else 0
                    )

                    if pd.notna(rating) and count > 0:
                        st.caption(
                            f":star: {float(rating):.1f}/5 · "
                            f"{count:,} lượt đánh giá"
                        )
                    else:
                        st.caption("Chưa có đánh giá")

                    is_selected = movie_id in selected_set

                    label = (
                        "✓ Đã chọn · Bỏ chọn"
                        if is_selected
                        else "+ Thêm vào yêu thích"
                    )

                    if st.button(
                        label,
                        key=f"toggle_{user_id}_{movie_id}",
                        width="stretch",
                    ):
                        _toggle_movie(
                            selection_key, movie_id
                        )
                        st.rerun()

    # ======================================
    # LƯU VÀ CHUYỂN SANG TRANG GỢI Ý
    # ======================================

    st.divider()

    current_selection = st.session_state[selection_key]

    save_col, skip_col = st.columns([3, 1])

    with save_col:
        st.button(
            "Lưu sở thích và xem gợi ý",
            key=f"save_favorites_{user_id}",
            type="primary",
            width="stretch",
            disabled=(
                len(set(map(int, current_selection)))
                < MIN_FAVORITES
            ),
            on_click=_save_favorites,
            args=(int(user_id), selection_key),
        )

        if len(current_selection) < MIN_FAVORITES:
            st.caption(
                f"Chọn thêm "
                f"{MIN_FAVORITES - len(current_selection)} "
                f"phim để nhận gợi ý."
            )

    with skip_col:
        if first_time and st.button(
            "Để sau",
            key=f"skip_favorites_{user_id}",
            width="stretch",
        ):

            st.session_state[selection_key] = (
                get_user_favorite_movie_ids(user_id)
            )

            mark_onboarding_completed(user_id)

            st.session_state["main_navigation"] = "Gợi ý phim"
            st.session_state["scroll_to_top"] = True

            st.rerun()