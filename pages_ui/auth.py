import streamlit as st
from src.database import init_db, register_user, authenticate_user

init_db()   # Tạo cơ sở dữ liệu nếu chưa tồn tại


def show_auth_page():
    """
    Hiển thị giao diện đăng nhập/đăng ký
    và trang chính sau khi đăng nhập.
    """

    if st.session_state.user_id is not None:
        st.title("Đăng nhập hoặc tạo tài khoản")

        st.success(f"Xin chào, {st.session_state.username}!")

        st.write("Bạn đã đăng nhập thành công.")

        st.subheader("Trang chủ")

        # Nút đăng xuất
        if st.button("Đăng xuất"):
            st.session_state.user_id = None
            st.session_state.username = None

            st.rerun()

    else:
        st.title("Đăng nhập hoặc tạo tài khoản")
        st.write("Để sử dụng hệ thống.")

        # Tạo hai tab giao diện
        tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])

        # =================================
        # TAB ĐĂNG NHẬP
        # =================================
        with tab_login:
            st.subheader("Đăng nhập tài khoản")

            with st.form("login_form"):
                login_username = st.text_input(
                    "Tên đăng nhập", key="login_username")
                login_password = st.text_input(
                    "Mật khẩu", type="password", key="login_password")

                login_submit = st.form_submit_button(
                    "Đăng nhập", width="stretch")

            # Kiểm tra khi người dùng nhấn nút
            if login_submit:
                if (not login_username.strip() or not login_password):
                    st.error("Vui lòng nhập đầy đủ thông tin.")

                else:
                    user = authenticate_user(login_username, login_password)

                    if user is not None:
                        # Lưu trạng thái đăng nhập
                        st.session_state.user_id = user["id"]

                        st.session_state.username = (user["username"])

                        # Chạy lại giao diện
                        st.rerun()

                    else:
                        st.error("Tên đăng nhập hoặc mật khẩu không đúng.")

        # =================================
        # TAB ĐĂNG KÝ
        # =================================
        with tab_register:
            st.subheader("Tạo tài khoản mới")
            with st.form("register_form"):
                register_username = st.text_input(
                    "Tên đăng nhập", key="register_username")
                register_email = st.text_input("Email", key="register_email")
                register_password = st.text_input(
                    "Mật khẩu", type="password", key="register_password")
                confirm_password = st.text_input(
                    "Nhập lại mật khẩu", type="password", key="confirm_password")

                register_submit = st.form_submit_button(
                    "Đăng ký", width="stretch")

            # Kiểm tra khi người dùng nhấn nút
            if register_submit:

                username = register_username.strip()
                email = register_email.strip()

                # Kiểm tra thông tin bắt buộc
                if (not username or not email or not register_password):
                    st.error("Vui lòng nhập đầy đủ thông tin.")

                # Kiểm tra độ dài tên đăng nhập
                elif len(username) < 3:
                    st.error("Tên đăng nhập phải có ít nhất 3 ký tự.")

                # Kiểm tra định dạng email cơ bản
                elif ("@" not in email or "." not in email.split("@")[-1]):
                    st.error("Vui lòng nhập email hợp lệ.")

                # Kiểm tra độ dài mật khẩu
                elif len(register_password) < 6:
                    st.error("Mật khẩu phải có ít nhất 6 ký tự.")

                # Kiểm tra mật khẩu xác nhận
                elif register_password != confirm_password:
                    st.error("Hai mật khẩu không khớp.")

                # Đăng ký tài khoản
                else:
                    success, message = register_user(
                        username, email, register_password)
                    if success:
                        st.success(message)
                        st.info(
                            "Hãy chuyển sang tab Đăng nhập "
                            "để sử dụng tài khoản vừa tạo."
                        )

                    else:
                        st.error(message)
