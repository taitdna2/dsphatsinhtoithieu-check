import io
import pandas as pd
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
st.caption("Bản v0 – Bước 1–2 & xử lý 2 file trưng bày (chưa xử lý doanh số & trạng thái).")

# ---------- helpers ----------
REQUIRED_COLS_STD = [
    "Mã CTTB", "Mã NPP", "Tên NPP", "Mã khách hàng", "Tên khách hàng",
    "Giai đoạn", "Số suất đăng ký"
]

def read_display_excel(file, month_label: str) -> pd.DataFrame:
    """
    Đọc 1 file trưng bày, lấy đúng các cột:
      B: Mã CTTB
      F: Mã NPP
      G: Tên NPP
      H: Giai đoạn
      K: Mã khách hàng
      L: Tên khách hàng
      T: Số suất đăng ký
    Trả về DF chuẩn hoá + thêm cột 'Tháng' = month_label
    """
    # ưu tiên đọc theo vị trí cột chữ cái
    df = pd.read_excel(file, usecols="B,F,G,H,K,L,T")
    # cố gắng đặt tên cột chuẩn (nhiều file có header lệch/khác)
    rename_map_candidates = [
        # nếu đã đúng tên thì không đổi
        dict(zip(df.columns, ["Mã CTTB","Mã NPP","Tên NPP","Giai đoạn","Mã khách hàng","Tên khách hàng","Số suất đăng ký"])),
        # vài biến thể hay gặp
        {
            df.columns[0]: "Mã CTTB",
            df.columns[1]: "Mã NPP",
            df.columns[2]: "Tên NPP",
            df.columns[3]: "Giai đoạn",
            df.columns[4]: "Mã khách hàng",
            df.columns[5]: "Tên khách hàng",
            df.columns[6]: "Số suất đăng ký",
        },
    ]
    # chọn map đầu tiên thoả yêu cầu
    df.columns = list(rename_map_candidates[0].values())

    # lọc các dòng rỗng mã KH
    df["Mã khách hàng"] = df["Mã khách hàng"].astype(str).str.strip()
    df = df[df["Mã khách hàng"].ne("").astype(bool)].copy()

    # chuẩn hoá kiểu dữ liệu
    for c in ["Giai đoạn", "Số suất đăng ký"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Tháng"] = month_label
    # giữ lại đúng thứ tự cột tiêu chuẩn
    df = df[["Tháng"] + REQUIRED_COLS_STD]
    return df

def combine_two_months(d1: pd.DataFrame, d2: pd.DataFrame, m1: str, m2: str) -> pd.DataFrame:
    """
    Gộp 2 DF trưng bày:
    - Key gộp: Mã CTTB, Mã NPP, Tên NPP, Mã KH, Tên KH
    - Cột kết quả: Giai đoạn – m1, Giai đoạn – m2  (lấy từ 'Số suất đăng ký' theo từng tháng)
    - Chừa sẵn cột Doanh số – m1/m2 (để xử lý sau), TRẠNG THÁI (để sau)
    """
    base_cols = ["Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng"]
    # lấy số suất theo tháng
    d1_slots = (d1.groupby(base_cols, as_index=False)["Số suất đăng ký"].sum()
                  .rename(columns={"Số suất đăng ký": f"Giai đoạn - {m1}"}))
    d2_slots = (d2.groupby(base_cols, as_index=False)["Số suất đăng ký"].sum()
                  .rename(columns={"Số suất đăng ký": f"Giai đoạn - {m2}"}))

    out = pd.merge(d1_slots, d2_slots, on=base_cols, how="outer").fillna(0)
    # ép int cho đẹp
    out[f"Giai đoạn - {m1}"] = out[f"Giai đoạn - {m1}"].astype(int)
    out[f"Giai đoạn - {m2}"] = out[f"Giai đoạn - {m2}"].astype(int)

    # thêm cột doanh số & trạng thái (để trống – sẽ điền ở bước sau)
    out[f"Doanh số - {m1}"] = ""
    out[f"Doanh số - {m2}"] = ""
    out["TRẠNG THÁI"] = ""

    # sắp xếp cho dễ nhìn
    out = out[[ "Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng",
                f"Giai đoạn - {m1}", f"Giai đoạn - {m2}",
                f"Doanh số - {m1}", f"Doanh số - {m2}", "TRẠNG THÁI" ]]
    return out.sort_values(["Mã NPP","Tên NPP","Tên khách hàng"]).reset_index(drop=True)

# ---------- UI ----------
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

    # (giữ chỗ cho doanh số – sẽ dùng sau)
    st.markdown("**Upload 2 file doanh số (tương ứng với 2 tháng trên)**")
    ds1 = st.file_uploader(f"[{prog}] File doanh số - {m1 or 'Tháng thứ 1'}", type=["xlsx"], key=f"{prog}_ds1")
    ds2 = st.file_uploader(f"[{prog}] File doanh số - {m2 or 'Tháng thứ 2'}", type=["xlsx"], key=f"{prog}_ds2")

    # ---- XỬ LÝ TRƯNG BÀY (CHỈ PHẦN NÀY) ----
    if m1 and m2 and tb1 and tb2:
        if st.button(f"Xử lý 2 file trưng bày cho CT {prog}", key=f"{prog}_process_tb"):
            try:
                df1 = read_display_excel(tb1, m1)
                df2 = read_display_excel(tb2, m2)

                result = combine_two_months(df1, df2, m1, m2)

                st.success("✅ Đã xử lý xong phần TRƯNG BÀY (chưa điền doanh số & trạng thái).")
                st.dataframe(result, use_container_width=True)

                # cho tải xuống bản nháp CSV để bạn kiểm tra nhanh
                csv = result.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="⬇️ Tải bản nháp (CSV) – Trưng bày 2 tháng",
                    data=csv,
                    file_name=f"{prog}_trungbay_{m1}_{m2}.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(f"Lỗi khi đọc/gộp file trưng bày: {e}")
    else:
        st.info("Nhập tên 2 tháng và upload đủ 2 file trưng bày để xử lý bước này.")
