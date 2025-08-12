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
st.caption("v0.2 — TRƯNG BÀY + DOANH SỐ + TRẠNG THÁI cho CT NMCD.")

# ===== Helpers =====
BASE_COLS = ["Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng"]

def read_display_excel(file) -> pd.DataFrame:
    """Đọc file trưng bày từ hàng 3 (skiprows=2), giữ cột H=Giai đoạn, lấy B,F,G,H,K,L,T."""
    df = pd.read_excel(file, usecols="B,F,G,H,K,L,T", skiprows=2, engine="openpyxl")
    df.columns = [
        "Mã CTTB","Mã NPP","Tên NPP","Giai đoạn",
        "Mã khách hàng","Tên khách hàng","Số suất đăng ký"
    ]
    for c in ["Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng","Giai đoạn"]:
        df[c] = df[c].astype(str).str.strip()
    df = df[(df["Mã CTTB"]!="") & (df["Mã khách hàng"]!="") & (df["Giai đoạn"]!="")].copy()
    df["Số suất đăng ký"] = pd.to_numeric(df["Số suất đăng ký"], errors="coerce").fillna(0).astype(int)
    return df[["Giai đoạn"] + BASE_COLS + ["Số suất đăng ký"]]

def extract_month_label(df: pd.DataFrame) -> str:
    """Lấy nhãn tháng từ cột 'Giai đoạn' (dùng giá trị phổ biến nhất)."""
    vals = df["Giai đoạn"].dropna().astype(str).str.strip()
    if vals.empty: return "Tháng ?"
    try:
        return vals.mode().iloc[0]
    except Exception:
        return vals.iloc[0]

def combine_two_months(d1: pd.DataFrame, d2: pd.DataFrame):
    """Trả về (out, m1, m2) – out là bảng gộp 2 tháng, m1/m2 là nhãn tháng."""
    m1 = extract_month_label(d1)
    m2 = extract_month_label(d2)

    d1_slots = (d1.groupby(BASE_COLS, as_index=False)["Số suất đăng ký"]
                  .sum().rename(columns={"Số suất đăng ký": f"Giai đoạn - {m1}"}))
    d2_slots = (d2.groupby(BASE_COLS, as_index=False)["Số suất đăng ký"]
                  .sum().rename(columns={"Số suất đăng ký": f"Giai đoạn - {m2}"}))

    out = d1_slots.merge(d2_slots, on=BASE_COLS, how="outer").fillna(0)
    out[f"Giai đoạn - {m1}"] = out[f"Giai đoạn - {m1}"].astype(int)
    out[f"Giai đoạn - {m2}"] = out[f"Giai đoạn - {m2}"].astype(int)

    out[f"Doanh số - {m1}"] = 0
    out[f"Doanh số - {m2}"] = 0
    out["TRẠNG THÁI"] = ""

    cols = BASE_COLS + [f"Giai đoạn - {m1}", f"Giai đoạn - {m2}",
                        f"Doanh số - {m1}", f"Doanh số - {m2}", "TRẠNG THÁI"]
    out = out[cols].sort_values(["Mã NPP","Tên NPP","Tên khách hàng"]).reset_index(drop=True)
    return out, m1, m2

def read_sales_excel(file, program_sheet_name: str) -> pd.DataFrame:
    """Đọc file doanh số: chỉ sheet trùng tên chương trình (ví dụ 'NMCD').
       Trả về cột: 'Mã khách hàng', 'Tổng Doanh số' (đã cộng gộp theo KH)."""
    xls = pd.ExcelFile(file, engine="openpyxl")
    sheets_lower = {s.lower(): s for s in xls.sheet_names}
    if program_sheet_name.lower() not in sheets_lower:
        raise ValueError(f"Không thấy sheet '{program_sheet_name}' trong file doanh số. Sheets: {', '.join(xls.sheet_names)}")
    sheet = sheets_lower[program_sheet_name.lower()]
    df = pd.read_excel(xls, sheet_name=sheet)

    # đoán cột mã KH
    id_candidates = [c for c in df.columns if str(c).strip().lower() in
        ["mã khách hàng","ma khach hang","mã kh","ma kh","customerid","customer id","makh","ma_kh","mã_kh"]]
    if not id_candidates:
        raise ValueError("Không tìm thấy cột Mã khách hàng trong file doanh số")
    col_id = id_candidates[0]

    # đoán cột tổng doanh số
    sales_candidates = [c for c in df.columns if str(c).strip().lower() in
        ["tổng doanh số","tong doanh so","tongdoanhso","doanh so","doanh_số","sum sales","sales"]]
    if not sales_candidates:
        raise ValueError("Không tìm thấy cột 'Tổng Doanh số' trong file doanh số")
    col_sales = sales_candidates[0]

    out = df[[col_id, col_sales]].copy()
    out.columns = ["Mã khách hàng","Tổng Doanh số"]
    out["Mã khách hàng"] = out["Mã khách hàng"].astype(str).str.strip()
    out["Tổng Doanh số"] = pd.to_numeric(out["Tổng Doanh số"], errors="coerce").fillna(0)
    out = out.groupby("Mã khách hàng", as_index=False)["Tổng Doanh số"].sum()
    return out

# ---- TÍNH TRẠNG THÁI CHO CT NMCD ----
def apply_status_nmcd(df: pd.DataFrame, m1: str, m2: str, per_slot_min: int = 150_000) -> pd.DataFrame:
    s1_col = f"Giai đoạn - {m1}"
    s2_col = f"Giai đoạn - {m2}"
    d1_col = f"Doanh số - {m1}"
    d2_col = f"Doanh số - {m2}"

    # mức tối thiểu theo số suất (1 suất=150k, 2 suất=300k)
    min1 = df[s1_col].astype(int) * per_slot_min
    min2 = df[s2_col].astype(int) * per_slot_min

    # tham gia?
    join1 = df[s1_col].astype(int) > 0
    join2 = df[s2_col].astype(int) > 0

    meet1 = (df[d1_col].astype(int) >= min1) & join1
    meet2 = (df[d2_col].astype(int) >= min2) & join2

    # rule:
    # - nếu không tham gia đủ 2 tháng -> Không xét
    # - nếu cả 2 tháng đều không đạt -> Không Đạt
    # - ngược lại -> Đạt
    status = []
    for j1, j2, ok1, ok2 in zip(join1, join2, meet1, meet2):
        if not (j1 and j2):
            status.append("Không xét")
        elif (not ok1) and (not ok2):
            status.append("Không Đạt")
        else:
            status.append("Đạt")

    df_out = df.copy()
    df_out["TRẠNG THÁI"] = status

    # (tuỳ chọn) thêm 2 cột mức tối thiểu để bạn nhìn rõ
    df_out[f"Tối thiểu - {m1}"] = min1
    df_out[f"Tối thiểu - {m2}"] = min2
    return df_out

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

    st.markdown("**Upload 2 file TRƯNG BÀY (2 tháng bất kỳ – app lấy tháng từ cột H 'Giai đoạn')**")
    tb1 = st.file_uploader(f"[{prog}] File trưng bày #1", type=["xlsx"], key=f"{prog}_tb1")
    tb2 = st.file_uploader(f"[{prog}] File trưng bày #2", type=["xlsx"], key=f"{prog}_tb2")

    st.markdown("**Upload 2 file DOANH SỐ (sheet phải trùng tên CT, ví dụ 'NMCD')**")
    ds1 = st.file_uploader(f"[{prog}] File doanh số #1", type=["xlsx"], key=f"{prog}_ds1")
    ds2 = st.file_uploader(f"[{prog}] File doanh số #2", type=["xlsx"], key=f"{prog}_ds2")

    if tb1 and tb2 and st.button(f"Xử lý CT {prog}", key=f"{prog}_process"):
        try:
            # Trưng bày
            df1 = read_display_excel(tb1)
            df2 = read_display_excel(tb2)
            st.write(f"📄 {prog} – Trưng bày: file #1 = {len(df1)} dòng, file #2 = {len(df2)} dòng")
            result, m1, m2 = combine_two_months(df1, df2)

            # Doanh số (nếu có)
            if ds1:
                s1 = read_sales_excel(ds1, program_sheet_name=prog)
                result = result.merge(s1, on="Mã khách hàng", how="left")
                result[f"Doanh số - {m1}"] = result["Tổng Doanh số"].fillna(0)
                result.drop(columns=["Tổng Doanh số"], inplace=True, errors="ignore")
            if ds2:
                s2 = read_sales_excel(ds2, program_sheet_name=prog)
                result = result.merge(s2, on="Mã khách hàng", how="left")
                if "Tổng Doanh số" in result.columns:
                    result.rename(columns={"Tổng Doanh số": "_Tổng Doanh số 2"}, inplace=True)
                    result[f"Doanh số - {m2}"] = result["_Tổng Doanh số 2"].fillna(0)
                    result.drop(columns=["_Tổng Doanh số 2"], inplace=True, errors="ignore")

            # Ép số int cho đẹp
            for c in [f"Doanh số - {m1}", f"Doanh số - {m2}"]:
                result[c] = pd.to_numeric(result[c], errors="coerce").fillna(0).astype(int)

            # Trạng thái theo từng CT
            if prog == "NMCD":
                result = apply_status_nmcd(result, m1, m2, per_slot_min=150_000)
            else:
                # tạm để trống cho CT khác
                result["TRẠNG THÁI"] = result.get("TRẠNG THÁI", "")

            st.success("✅ Hoàn tất (NMCD): đã ghép doanh số & tính trạng thái.")
            st.dataframe(result, use_container_width=True)

            # Tải xuống CSV
            csv = result.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Tải CSV – Kết quả",
                data=csv,
                file_name=f"{prog}_ketqua_{m1}_{m2}.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"Lỗi khi xử lý: {e}")
    else:
        st.info("Upload đủ 2 file trưng bày (và doanh số nếu có), rồi bấm nút để xử lý.")
