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
st.caption("v0 — Đã xử lý 2 file TRƯNG BÀY (đọc từ hàng 3, lấy tháng từ cột H–Giai đoạn). Chưa xử lý doanh số & trạng thái.")

# ===== Helpers =====
BASE_COLS = ["Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng"]

def read_display_excel(file) -> pd.DataFrame:
    """Đọc file trưng bày từ hàng 3 (skiprows=2), giữ nguyên cột H = Giai đoạn,
    lấy các cột: B,F,G,H,K,L,T."""
    df = pd.read_excel(
        file, usecols="B,F,G,H,K,L,T", skiprows=2, engine="openpyxl"
    )
    df.columns = [
        "Mã CTTB","Mã NPP","Tên NPP","Giai đoạn",
        "Mã khách hàng","Tên khách hàng","Số suất đăng ký"
    ]

    # chuẩn hoá text & loại dòng rỗng
    for c in ["Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng","Giai đoạn"]:
        df[c] = df[c].astype(str).str.strip()
    df = df[(df["Mã CTTB"]!="") & (df["Mã khách hàng"]!="") & (df["Giai đoạn"]!="")].copy()

    # số suất
    df["Số suất đăng ký"] = pd.to_numeric(df["Số suất đăng ký"], errors="coerce").fillna(0).astype(int)
    return df[["Giai đoạn"] + BASE_COLS + ["Số suất đăng ký"]]

def extract_month_label(df: pd.DataFrame) -> str:
    """Lấy nhãn tháng từ cột 'Giai đoạn' (giả định mỗi file chỉ 1 tháng).
    Dùng giá trị phổ biến nhất để an toàn."""
    vals = df["Giai đoạn"].dropna().astype(str).str.strip()
    if vals.empty:
        return "Tháng ?"
    # lấy mode() nếu đồng nhất; fallback lấy giá trị đầu
    try:
        label = vals.mode().iloc[0]
    except Exception:
        label = vals.iloc[0]
    return label

def combine_two_months(d1: pd.DataFrame, d2: pd.DataFrame) -> pd.DataFrame:
    """Gộp 2 tháng: tạo cột 'Giai đoạn - <m1>' & 'Giai đoạn - <m2>' từ 'Số suất đăng ký'."""
    m1 = extract_month_label(d1)
    m2 = extract_month_label(d2)

    d1_slots = (d1.groupby(BASE_COLS, as_index=False)["Số suất đăng ký"]
                  .sum().rename(columns={"Số suất đăng ký": f"Giai đoạn - {m1}"}))
    d2_slots = (d2.groupby(BASE_COLS, as_index=False)["Số suất đăng ký"]
                  .sum().rename(columns={"Số suất đăng ký": f"Giai đoạn - {m2}"}))

    out = d1_slots.merge(d2_slots, on=BASE_COLS, how="outer").fillna(0)
    out[f"Giai đoạn - {m1}"] = out[f"Giai đoạn - {m1}"].astype(int)
    out[f"Giai đoạn - {m2}"] = out[f"Giai đoạn - {m2}"].astype(int)

    # chừa chỗ doanh số + trạng thái (sẽ xử lý sau)
    out[f"Doanh số - {m1}"] = ""
    out[f"Doanh số - {m2}"] = ""
    out["TRẠNG THÁI"] = ""

    cols = BASE_COLS + [f"Giai đoạn - {m1}", f"Giai đoạn - {m2}",
                        f"Doanh số - {m1}", f"Doanh số - {m2}", "TRẠNG THÁI"]
    return out[cols].sort_values(["Mã NPP","Tên NPP","Tên khách hàng"]).reset_index(drop=True)

# ===== UI =====
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

    st.markdown("**Upload 2 file TRƯNG BÀY (2 tháng bất kỳ – app tự lấy tháng từ cột H ‘Giai đoạn’)**")
    tb1 = st.file_uploader(f"[{prog}] File trưng bày #1", type=["xlsx"], key=f"{prog}_tb1")
    tb2 = st.file_uploader(f"[{prog}] File trưng bày #2", type=["xlsx"], key=f"{prog}_tb2")

    # (giữ chỗ – doanh số sẽ thêm sau)
    st.markdown("**Upload 2 file DOANH SỐ (tương ứng 2 tháng trên)**")
    ds1 = st.file_uploader(f"[{prog}] File doanh số #1", type=["xlsx"], key=f"{prog}_ds1")
    ds2 = st.file_uploader(f"[{prog}] File doanh số #2", type=["xlsx"], key=f"{prog}_ds2")

    if tb1 and tb2 and st.button(f"Xử lý 2 file TRƯNG BÀY cho CT {prog}", key=f"{prog}_process_tb"):
        try:
            df1 = read_display_excel(tb1)
            df2 = read_display_excel(tb2)
            st.write(f"📄 #{prog} – Đọc được: file #1 = {len(df1)} dòng, file #2 = {len(df2)} dòng")

            result = combine_two_months(df1, df2)

            st.success("✅ Đã xử lý xong phần TRƯNG BÀY (chưa điền doanh số & trạng thái).")
            st.dataframe(result, use_container_width=True)

            csv = result.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Tải CSV – Trưng bày 2 tháng",
                data=csv,
                file_name=f"{prog}_trungbay_2thang.csv",
                mime="text/csv",
            )
        except Exception as e:
            st.error(f"Lỗi khi đọc/gộp file trưng bày: {e}")
    else:
        st.info("Upload đủ 2 file trưng bày rồi bấm nút để xử lý.")
