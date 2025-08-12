import streamlit as st

PROGRAMS = {
    "NMCD": "Nước mắm cao đạm",
    "DHLM": "Dầu hào, Nước tương",
    "KOS&XX": "Cá KOS & Xúc xích",
    "GVIG": "Gia vị gói",
    "LTLKC": "Lẩu Thái & Lẩu Kim chi",
}

st.set_page_config(page_title="Xử lý dữ liệu trưng bày", layout="wide")
st.title("📊 Xử lý dữ liệu Trưng bày & Doanh số")
st.caption("Bản v0 – Bước 1–2: chọn CT & upload file. Khi ok UI, sẽ thêm xử lý + export.")

selected_programs = st.multiselect(
    "Chọn chương trình cần xử lý:",
    options=list(PROGRAMS.keys()),
    format_func=lambda x: f"{x} - {PROGRAMS[x]}",
)

if not selected_programs:
    st.info("Chọn ít nhất 1 chương trình để bắt đầu.")
    st.stop()

st.success(f"Đã chọn: {', '.join(selected_programs)}")

for prog in selected_programs:
    st.markdown("---")
    st.subheader(f"📌 Xử lý CT: {prog} - {PROGRAMS[prog]}")

    c1, c2 = st.columns(2)
    with c1:
        m1 = st.text_input(f"[{prog}] Tên tháng thứ 1 (VD: Tháng 06/2025)", key=f"{prog}_m1")
    with c2:
        m2 = st.text_input(f"[{prog}] Tên tháng thứ 2 (VD: Tháng 07/2025)", key=f"{prog}_m2")

    st.markdown("**Upload 2 file trưng bày (tương ứng 2 tháng muốn xử lý)**")
    tb1 = st.file_uploader(f"[{prog}] File trưng bày - {m1 or 'Tháng thứ 1'}", type=["xlsx"], key=f"{prog}_tb1")
    tb2 = st.file_uploader(f"[{prog}] File trưng bày - {m2 or 'Tháng thứ 2'}", type=["xlsx"], key=f"{prog}_tb2")

    st.markdown("**Upload 2 file doanh số (tương ứng với 2 tháng trên)**")
    ds1 = st.file_uploader(f"[{prog}] File doanh số - {m1 or 'Tháng thứ 1'}", type=["xlsx"], key=f"{prog}_ds1")
    ds2 = st.file_uploader(f"[{prog}] File doanh số - {m2 or 'Tháng thứ 2'}", type=["xlsx"], key=f"{prog}_ds2")

    ready = all([m1, m2, tb1, tb2, ds1, ds2])
    if ready:
        st.info(f"✅ Sẵn sàng xử lý CT {prog}. (Bản kế tiếp sẽ có nút Xử lý & Tải về)")
    else:
        st.warning(f"Nhập đủ **tên 2 tháng** và upload đủ **4 file** cho CT {prog}.")
