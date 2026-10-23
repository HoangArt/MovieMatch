import streamlit as st
from src.common import context, enrich, translate_genres, shorten_text
from pages_ui.movie_display import load_poster_data, show_movie_poster
from src.content_recommender import recommend_by_favorite_movies
from src.database import get_user_favorite_movie_ids

def show_recommendations_page(user_id):
    """Hiển thị gợi ý cold-start kèm poster lấy từ TMDB."""
    st.title("Gợi ý phim dành cho bạn")
    favorite_ids = get_user_favorite_movie_ids(user_id)

    if favorite_ids:
        movies, ratings, _ = context()
        movie_data = enrich(movies, ratings)
        selected = movie_data[movie_data["movieId"].isin(favorite_ids)]
        st.write("Dựa trên các phim bạn yêu thích:")
        st.caption(" · ".join(selected["title"].tolist()))

        try:
            recommendations = recommend_by_favorite_movies(
                favorite_ids,
                top_k=12,
            )
        except Exception as exc:
            st.error("Chưa thể tạo gợi ý theo nội dung từ dữ liệu phim.")
            st.caption(str(exc))
            return

        if recommendations.empty:
            st.info("Chưa có phim tương tự phù hợp trong dữ liệu.")
            return

        # Mô hình trả về movieId/title/genres/similarity.
        # Ghép tmdbId để tiện ích dùng chung có thể tải poster.
        tmdb_lookup = movies[["movieId", "tmdbId"]].drop_duplicates("movieId")
        recommendations = recommendations.merge(
            tmdb_lookup,
            on="movieId",
            how="left",
        )
        poster_data = load_poster_data(recommendations)

        st.caption(
            "Cách gợi ý: TF-IDF từ tên phim, thể loại và tags; "
            "sắp xếp theo độ tương đồng cosine. Đây là gợi ý cold-start, "
            "chưa sử dụng lịch sử chấm điểm cá nhân."
        )
        columns = st.columns(3)
        for index, (_, movie) in enumerate(recommendations.iterrows()):
            with columns[index % 3]:
                with st.container(border=True):
                    show_movie_poster(movie, poster_data, width=None)
                    
                    st.write(f"**{shorten_text(movie["title"])}**")

                    
                    st.caption(f"**{shorten_text(translate_genres(movie["genres"]), max_chars=55)}**")

                    st.metric(
                        "Độ tương đồng nội dung",
                        f"{float(movie['similarity']) * 100:.1f}%",
                    )
    else:
        st.info(
            "Bạn chưa lưu phim yêu thích. Hãy chọn vài phim để hệ thống "
            "cá nhân hóa gợi ý theo nội dung."
        )
        movies, ratings, _ = context()
        popular = enrich(movies, ratings).sort_values(
            ["count", "score"], ascending=[False, False]
        ).head(12)
        poster_data = load_poster_data(popular)

        st.subheader("Phim phổ biến để bắt đầu")
        columns = st.columns(3)
        for index, (_, movie) in enumerate(popular.iterrows()):
            with columns[index % 3]:
                with st.container(border=True):
                    show_movie_poster(movie, poster_data, width=None)
                    st.write(f"**{movie['title']}**")
                    st.caption(translate_genres(movie["genres"]))
                    if int(movie["count"]) > 0:
                        st.caption(
                            f"⭐ {float(movie['mean']):.1f}/5 · "
                            f"{int(movie['count']):,} lượt"
                        )