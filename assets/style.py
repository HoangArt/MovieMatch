MOVIE_DETAIL_CSS = """
<style>
/* Banner phim */
.cm-detail-hero {
    position: relative !important;
    display: flex !important;
    align-items: center !important;

    width: 100% !important;
    min-height: 330px !important;
    height: auto !important;
    max-height: none !important;

    margin: 0 0 22px 0 !important;
    padding: 36px 42px !important;

    box-sizing: border-box !important;
    border-radius: 18px !important;

    background-size: cover !important;
    background-position: center !important;
    background-repeat: no-repeat !important;

    overflow: hidden !important;
    isolation: isolate;
}

/* Phần chữ trên banner */
.cm-detail-hero-content {
    position: relative !important;
    z-index: 2 !important;

    width: 100% !important;
    max-width: 640px !important;

    margin: 0 !important;
    padding: 0 !important;

    top: auto !important;
    left: auto !important;
    bottom: auto !important;
    right: auto !important;

    transform: none !important;
}

/* Nhãn CineMatch */
.cm-detail-label {
    color: #ff4b55;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin-bottom: 12px;
}

/* Tên phim */
.cm-detail-hero h1 {
    color: #ffffff !important;
    font-size: clamp(27px, 3.2vw, 46px) !important;
    font-weight: 800 !important;
    line-height: 1.18 !important;
    margin: 0 0 14px !important;
    overflow-wrap: anywhere;
}

/* Điểm đánh giá */
.cm-detail-hero-rating {
    color: #ffd34d !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    margin: 0 0 9px !important;
}

/* Năm và thể loại */
.cm-detail-hero-year {
    color: #e5e5e5 !important;
    font-size: 14px !important;
    margin: 0 0 12px !important;
    line-height: 1.6 !important;
}

/* Mô tả ngắn */
.cm-detail-hero-description {
    color: #eeeeee !important;
    font-size: 15px !important;
    line-height: 1.65 !important;

    display: -webkit-box !important;
    -webkit-box-orient: vertical !important;
    -webkit-line-clamp: 5 !important;
    line-clamp: 5 !important;

    overflow: hidden !important;
    margin: 0 !important;
}

/* Thẻ thông tin */
.cm-detail-info-card {
    padding: 22px 24px;
    border-radius: 16px;
    background: #17171e;
    border: 1px solid rgba(255,255,255,.08);
    margin-bottom: 16px;
}

.cm-detail-info-title {
    font-size: 22px;
    font-weight: 800;
    color: white;
    margin-bottom: 18px;
}

.cm-detail-info-row {
    display: flex;
    gap: 12px;
    padding: 9px 0;
    border-bottom: 1px solid rgba(255,255,255,.07);
    line-height: 1.6;
}

.cm-detail-info-row:last-child {
    border-bottom: none;
}

.cm-detail-info-label {
    width: 145px;
    flex-shrink: 0;
    color: #a7a7b3;
    font-size: 14px;
}

.cm-detail-info-value {
    flex: 1;
    color: #f4f4f5;
    font-size: 14px;
    font-weight: 600;
    overflow-wrap: anywhere;
}

/* Diễn viên */
.cm-cast-card {
    width: 100%;
    overflow: hidden;
    border-radius: 13px;
    background: #191920;
    border: 1px solid rgba(255,255,255,.07);
    margin-bottom: 12px;
}

.cm-cast-photo {
    width: 100%;
    aspect-ratio: 2 / 3;
    overflow: hidden;
    background: #24242e;
}

.cm-cast-photo img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
}

.cm-cast-no-image {
    display: flex;
    width: 100%;
    height: 100%;
    align-items: center;
    justify-content: center;
    font-size: 36px;
}

.cm-cast-name {
    padding: 10px 9px 3px;
    font-size: 13px;
    font-weight: 700;
    color: white;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.cm-cast-role {
    padding: 0 9px 12px;
    color: #a9a9b2;
    font-size: 12px;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

/* Màn hình nhỏ */
@media (max-width: 768px) {

    .cm-detail-hero {
        min-height: 270px !important;
        padding: 24px !important;
    }

    .cm-detail-hero h1 {
        font-size: 27px !important;
    }

    .cm-detail-info-card {
        padding: 16px;
    }

    .cm-detail-info-row {
        flex-direction: column;
        gap: 2px;
    }

    .cm-detail-info-label {
        width: auto;
    }
}

</style>
"""

HOME_CSS = """
<style>

.home-movie-poster {
    display: block;
    width: 150px;
    height: 225px;
    overflow: hidden;
    border-radius: 10px;
    background: #252833;
    text-decoration: none !important;
    transition:
        transform 0.2s ease,
        box-shadow 0.2s ease;
}

.home-movie-poster:hover {
    transform: scale(1.04);
    box-shadow: 0 6px 18px rgba(255, 75, 75, 0.35);
}

.home-movie-poster img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

.home-no-poster {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    text-align: center;
    font-size: 13px;
}

</style>
"""

MOVIE_DETAIL_CSS = """
<style>

/* =========================================
   1. BỐ CỤC TOÀN TRANG
========================================= */

.stMainBlockContainer {
    max-width: 1200px;
    padding-top: 5rem;
    padding-bottom: 3rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* =========================================
   2. HEADER PHIM
========================================= */

.mm-detail-header {
    margin: 1.5rem 0 2rem 0;
}

.mm-eyebrow {
    margin-bottom: 0.6rem;
    letter-spacing: 0.15em;
    font-size: 0.75rem;
    font-weight: 700;
}

.mm-detail-title {
    margin: 0;
    font-size: clamp(1.8rem, 4vw, 2.8rem);
    font-weight: 800;
    line-height: 1.25;
    overflow-wrap: anywhere;
}

.mm-header-line {
    width: 65px;
    height: 3px;
    margin-top: 1rem;
    border-radius: 10px;
}

/* =========================================
   3. BỐ CỤC POSTER
========================================= */

[data-testid="stImage"] {
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
}

[data-testid="stImage"] img {
    display: block;
    width: 100%;
    height: auto;
    max-width: 100%;
    object-fit: contain;
}

/* =========================================
   4. THÔNG TIN PHIM
========================================= */

.mm-info-card {
    width: 100%;
    box-sizing: border-box;
    padding: 1.25rem;
}

.mm-info-heading {
    margin: 0 0 1.1rem 0;
    font-size: 1.25rem;
    font-weight: 750;
}

.mm-meta-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
}

.mm-meta-item {
    min-width: 0;
    box-sizing: border-box;
    padding: 0.85rem;
    overflow-wrap: anywhere;
}

.mm-meta-label {
    margin-bottom: 0.4rem;
    font-size: 0.8rem;
}

.mm-meta-value {
    font-size: 0.95rem;
    font-weight: 650;
    overflow-wrap: anywhere;
    word-break: break-word;
}

.mm-rating-value {
    font-size: 1.1rem;
    font-weight: 800;
}

.mm-tagline {
    margin-top: 1rem;
    line-height: 1.6;
    font-size: 0.9rem;
    font-style: italic;
}

/* =========================================
   5. NÚT TRANG PHIM
========================================= */

div.stLinkButton {
    margin-top: 1rem;
}

div.stLinkButton > a {
    width: fit-content;
    min-height: 42px;
    padding: 0.55rem 1rem;
}

/* =========================================
   6. TIÊU ĐỀ CÁC KHU VỰC
========================================= */

.mm-section {
    margin-top: 2.5rem;
    margin-bottom: 1rem;
}

.mm-section-label {
    margin-bottom: 0.4rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.15em;
}

.mm-section-title {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.45rem;
    font-weight: 750;
}

/* =========================================
   7. NỘI DUNG PHIM
========================================= */

.mm-overview-card {
    box-sizing: border-box;
    width: 100%;
    padding: 1.25rem 1.5rem;
    line-height: 1.85;
    font-size: 1rem;
    overflow-wrap: anywhere;
    word-break: break-word;
}

/* =========================================
   8. TRAILER
========================================= */

[data-testid="stVideo"] {
    width: 100%;
    max-width: 100%;
    overflow: hidden;
}

[data-testid="stVideo"] iframe {
    width: 100%;
    max-width: 100%;
    aspect-ratio: 16 / 9;
}

/* =========================================
   9. KHU VỰC ĐÁNH GIÁ
========================================= */

.mm-rating-section {
    width: 100%;
    box-sizing: border-box;
    padding: 1.2rem 1.4rem;
    margin: 1rem 0;
}

.mm-rating-title {
    margin-bottom: 0.4rem;
    font-size: 1.05rem;
    font-weight: 700;
}

.mm-rating-description {
    margin: 0;
    line-height: 1.6;
    font-size: 0.9rem;
}

/* =========================================
   10. BỐ CỤC CÁC CỘT
========================================= */

[data-testid="stHorizontalBlock"] {
    align-items: flex-start;
}

[data-testid="stColumn"] {
    min-width: 0;
}

</style>
"""