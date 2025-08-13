import pandas as pd
import streamlit as st
import numpy as np
from io import BytesIO

# ================== Cấu hình & Danh mục CT ==================
PROGRAMS = {
    "NMCD": "Nước mắm cao đạm",
    "DHLM": "Dầu hào, Nước tương",
    "KOS&XX": "Cá KOS & Xúc xích",
    "GVIG": "Gia vị gói",
    "LTLKC": "Lẩu Thái & Lẩu Kim chi",
}

st.set_page_config(page_title="Xử lý dữ liệu trưng bày", layout="wide")
# ===== UI THEME / HEADER =====
APP_VERSION = "v0.3"
APP_AUTHOR  = "© Nguyen Anh Tai"
PRIMARY_EMOJI = "📈"

st.markdown("""
<style>
/* Tăng chiều rộng, font, màu */
[data-testid="stAppViewContainer"] {padding-top: 0rem;}
:root { --brand: #2f6fed; --text: #1b1f23; --muted: #6b7280; }
h1.app-title {
  font-weight: 800; font-size: 44px; line-height: 1.1;
  margin: 0.15rem 0 0.4rem 0; letter-spacing: -0.02em;
  background: linear-gradient(90deg,#111827, #334155 60%, #6366f1);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
p.app-sub {
  color: var(--muted); margin: 0.2rem 0 1.1rem 0; font-size: 16px;
}
.badge {
  display:inline-block; padding: 4px 10px; border-radius: 999px;
  background:#eef2ff; color:#4338ca; font-weight:600; font-size:12px; margin-left:.5rem;
  border:1px solid #c7d2fe;
}
footer.app-footer {
  position: fixed; bottom: 12px; right: 18px;
  background: rgba(255,255,255,.75); backdrop-filter: blur(6px);
  border: 1px solid #e5e7eb; padding: 6px 10px; border-radius: 10px; font-size: 12px; color:#374151;
  box-shadow: 0 6px 24px rgba(0,0,0,.05);
}
.stDownloadButton, .stButton>button {
  border-radius: 10px !important; font-weight: 600 !important;
}
div[role="tablist"] button[role="tab"] { font-weight: 600; }
.st-emotion-cache-13k62yr { border-radius: 14px; } /* expander bo tròn */
thead tr th { position: sticky; top: 0; background: #fff; z-index: 1; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    f"""
    <h1 class="app-title">{PRIMARY_EMOJI} Xử lý dữ liệu Trưng bày &amp; Doanh số
      <span class="badge">{APP_VERSION}</span>
      <span class="badge">{APP_AUTHOR}</span>
    </h1>
    <p class="app-sub">Trưng bày + Doanh số + Trạng thái · Bộ lọc nâng cao · Xuất Excel chuẩn</p>
    """,
    unsafe_allow_html=True,
)
# Footer bản quyền (nhẹ nhàng, cố định góc phải dưới)
st.markdown(f'<footer class="app-footer">{APP_AUTHOR}</footer>', unsafe_allow_html=True)

# Thêm About vào sidebar
with st.sidebar:
    st.markdown("### ℹ️ About")
    st.markdown(
        f"- Tác giả: **Nguyen Anh Tai**  \n"
        f"- Phiên bản: **{APP_VERSION}**  \n"
        "- Tính năng: Trưng bày · Doanh số · Trạng thái · Lọc · Xuất Excel"
    )

# Chuẩn hoá tên sheet trong file Doanh số (tránh lệch như GVG, KOSXX)
SHEET_NAME_ALIASES = {
    "NMCD": "NMCD",
    "DHLM": "DHLM",
    "GVG": "GVIG",     # lưu GVG -> mình hiểu là GVIG
    "GVIG": "GVIG",
    "LTLKC": "LTLKC",
    "KOSXX": "KOS&XX", # lưu KOSXX -> mình hiểu là KOS&XX
    "KOS&XX": "KOS&XX",
}
# Mức tối thiểu / 1 suất theo CT (bạn đổi số ở đây nếu chính sách thay đổi)
PER_SLOT_MIN = {
    "NMCD": 150_000,  # Nước mắm cao đạm
    "DHLM": 100_000,  # Dầu hào, Nước tương
    "KOS&XX": 200_000,  # Cá KOS & Xúc xích
    "GVIG": 300_000,  # Gia vị gói (Miền Trung/Bắc)
    "LTLKC": 80_000,   # Lẩu Thái & Lẩu Kim chi
}
def _resolve_sheet_name(xls: pd.ExcelFile, program_code: str) -> str:
    """
    Trả về tên sheet thực tế trong file doanh số tương ứng với program_code.
    - Chấp nhận các alias: GVG~GVIG, KOSXX~KOS&XX
    - Không phân biệt hoa/thường, bỏ khoảng trắng dư.
    """
    # chuẩn hoá code được chọn
    want = SHEET_NAME_ALIASES.get(program_code.strip().upper(), program_code.strip().upper())

    # map sheet trong file -> dạng chuẩn để so
    norm2real = {}
    for s in xls.sheet_names:
        norm = s.strip().upper()
        norm = SHEET_NAME_ALIASES.get(norm, norm)  # đổi alias về tên chuẩn
        norm2real[norm] = s  # lưu lại tên thật trong file

    if want in norm2real:
        return norm2real[want]

    # fallback: thử so khớp gần đúng
    for norm, real in norm2real.items():
        if want in norm or norm in want:
            return real

    raise ValueError(
        f"Không tìm thấy sheet cho chương trình '{program_code}'. "
        f"Sheets có trong file: {', '.join(xls.sheet_names)}"
    )

# ================== Helpers ==================
BASE_COLS = ["Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng"]

def read_display_excel(file) -> pd.DataFrame:
    """Đọc file trưng bày từ hàng 3 (skiprows=2), giữ B,F,G,H,K,L,T (H=Giai đoạn)."""
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
    """Lấy nhãn tháng từ cột 'Giai đoạn' (giá trị phổ biến nhất)."""
    vals = df["Giai đoạn"].dropna().astype(str).str.strip()
    if vals.empty:
        return "Tháng ?"
    try:
        return vals.mode().iloc[0]
    except Exception:
        return vals.iloc[0]

def combine_two_months(d1: pd.DataFrame, d2: pd.DataFrame):
    """Gộp 2 tháng theo key BASE_COLS. Trả về (out, m1, m2)."""
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
    """
    Đọc file doanh số: chỉ sheet trùng tên chương trình (ví dụ 'NMCD').
    Tự chuẩn hoá alias sheet: GVG->GVIG, KOSXX->KOS&XX, ...
    Trả về: ['Mã khách hàng', 'Tổng Doanh số'] đã cộng gộp theo KH.
    """
    xls = pd.ExcelFile(file, engine="openpyxl")
    # tìm đúng sheet thực tế trong file theo program_sheet_name
    sheet = _resolve_sheet_name(xls, program_sheet_name)
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

def apply_status_generic(df: pd.DataFrame, m1: str, m2: str, per_slot_min: int) -> pd.DataFrame:
    s1_col = f"Giai đoạn - {m1}"
    s2_col = f"Giai đoạn - {m2}"
    d1_col = f"Doanh số - {m1}"
    d2_col = f"Doanh số - {m2}"

    df2 = df.copy()
    for c in [s1_col, s2_col, d1_col, d2_col]:
        df2[c] = pd.to_numeric(df2[c], errors="coerce").fillna(0).astype(int)

    min1 = df2[s1_col] * int(per_slot_min)
    min2 = df2[s2_col] * int(per_slot_min)

    join1 = df2[s1_col] > 0
    join2 = df2[s2_col] > 0

    meet1 = (df2[d1_col] >= min1) & join1
    meet2 = (df2[d2_col] >= min2) & join2

    status = []
    for j1, j2, ok1, ok2 in zip(join1, join2, meet1, meet2):
        if not (j1 and j2):
            status.append("Không xét")
        elif (not ok1) and (not ok2):
            status.append("Không Đạt")
        else:
            status.append("Đạt")

    df2["TRẠNG THÁI"] = status
    df2[f"Tối thiểu - {m1}"] = min1
    df2[f"Tối thiểu - {m2}"] = min2
    return df2


def apply_status_kosxx(df: pd.DataFrame, m1: str, m2: str,
                       min_mb: int = 200_000, min_other: int = 300_000) -> pd.DataFrame:
    """
    KOS&XX theo miền:
      - 'Mã NPP' chứa 'MB'  -> 200k/slot
      - Còn lại             -> 300k/slot
    """
    s1_col = f"Giai đoạn - {m1}"
    s2_col = f"Giai đoạn - {m2}"
    d1_col = f"Doanh số - {m1}"
    d2_col = f"Doanh số - {m2}"

    out = df.copy()
    for c in [s1_col, s2_col, d1_col, d2_col]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)

    npp = out["Mã NPP"].astype(str).str.upper()
    per_slot = np.where(npp.str.contains("MB", na=False), min_mb, min_other)

    min1 = out[s1_col] * per_slot
    min2 = out[s2_col] * per_slot

    join1 = out[s1_col] > 0
    join2 = out[s2_col] > 0

    meet1 = (out[d1_col] >= min1) & join1
    meet2 = (out[d2_col] >= min2) & join2

    status = []
    for j1, j2, ok1, ok2 in zip(join1, join2, meet1, meet2):
        if not (j1 and j2):
            status.append("Không xét")
        elif (not ok1) and (not ok2):
            status.append("Không Đạt")
        else:
            status.append("Đạt")

    out["TRẠNG THÁI"] = status
    out[f"Tối thiểu - {m1}"] = min1
    out[f"Tối thiểu - {m2}"] = min2
    return out

def export_excel_layout(df: pd.DataFrame, m1: str, m2: str, prog: str) -> bytes:
    """
    Xuất .xlsx:
    - Header gộp 2 hàng (Giai đoạn m1/m2, Doanh số m1/m2).
    - KHÔNG có hàng tiêu đề lặp ở dòng 3.
    - Tô màu TRẠNG THÁI, định dạng số & độ rộng cột.
    """
    from io import BytesIO
    import xlsxwriter

    cols = [
        "Mã CTTB","Mã NPP","Tên NPP","Mã khách hàng","Tên khách hàng",
        f"Giai đoạn - {m1}", f"Giai đoạn - {m2}",
        f"Doanh số - {m1}", f"Doanh số - {m2}", "TRẠNG THÁI"
    ]

    d = df.copy()
    for c in cols:
        if c not in d.columns:
            d[c] = ""
    d = d[cols].reset_index(drop=True)

    # Chuẩn hoá kiểu số
    for c in [f"Giai đoạn - {m1}", f"Giai đoạn - {m2}"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int)
    for c in [f"Doanh số - {m1}", f"Doanh số - {m2}"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        wb = writer.book
        ws = wb.add_worksheet(f"{prog}")

        # ==== formats ====
        header = wb.add_format({"bold": True,"align":"center","valign":"vcenter",
                                "border":1,"bg_color":"#00B0F0","font_color":"#FFFFFF"})
        sub = wb.add_format({"bold": True,"align":"center","valign":"vcenter",
                             "border":1,"bg_color":"#D9EDF7"})
        cell = wb.add_format({"border":1})
        center = wb.add_format({"border":1,"align":"center"})
        intfmt = wb.add_format({"border":1,"num_format":"#,##0"})
        okfmt  = wb.add_format({"border":1,"align":"center","bg_color":"#C6EFCE"})
        badfmt = wb.add_format({"border":1,"align":"center","bg_color":"#FFC7CE"})
        neut   = wb.add_format({"border":1,"align":"center","bg_color":"#F2F2F2"})

        # ==== header gộp (2 hàng) ====
        ws.merge_range(0,0,1,0,"Mã CTTB", header)
        ws.merge_range(0,1,1,1,"Mã NPP", header)
        ws.merge_range(0,2,1,2,"Tên NPP", header)
        ws.merge_range(0,3,1,3,"Mã khách hàng", header)
        ws.merge_range(0,4,1,4,"Tên khách hàng", header)
        ws.merge_range(0,5,0,6,"Giai đoạn", header)
        ws.merge_range(0,7,0,8,"Doanh số", header)
        ws.merge_range(0,9,1,9,"TRẠNG THÁI", header)

        # Hàng 2 (subheader) chỉ ghi tiêu đề con cho 4 cột nhóm
        ws.write(1,5, m1, sub)
        ws.write(1,6, m2, sub)
        ws.write(1,7, m1, sub)
        ws.write(1,8, m2, sub)

        # ==== data (bắt đầu từ hàng 3 - index 2) ====
        start_row = 2
        n = len(d)
        for i in range(n):
            r = start_row + i
            ws.write(r,0, d.iloc[i,0], cell)           # Mã CTTB
            ws.write(r,1, d.iloc[i,1], cell)           # Mã NPP
            ws.write(r,2, d.iloc[i,2], cell)           # Tên NPP
            ws.write(r,3, d.iloc[i,3], cell)           # Mã KH
            ws.write(r,4, d.iloc[i,4], cell)           # Tên KH
            ws.write_number(r,5, int(d.iloc[i,5]), center)   # Giai đoạn m1
            ws.write_number(r,6, int(d.iloc[i,6]), center)   # Giai đoạn m2
            ws.write_number(r,7, int(d.iloc[i,7]), intfmt)   # Doanh số m1
            ws.write_number(r,8, int(d.iloc[i,8]), intfmt)   # Doanh số m2

            stt = str(d.iloc[i,9]).strip()
            fmt = okfmt if stt == "Đạt" else badfmt if stt == "Không Đạt" else neut if stt == "Không xét" else center
            ws.write(r,9, stt, fmt)

        # width & freeze panes
        widths = [12,12,22,16,28,14,14,16,16,14]
        for c, w in enumerate(widths):
            ws.set_column(c, c, w)
        ws.freeze_panes(start_row, 0)
        ws.set_footer('&R© Nguyen Anh Tai')

    return buf.getvalue()

# ================== UI / Main ==================
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

    # Upload
    st.markdown("**Upload 2 file TRƯNG BÀY (App tự lấy tháng từ cột H 'Giai đoạn')**")
    tb1 = st.file_uploader(f"[{prog}] File trưng bày #1", type=["xlsx"], key=f"{prog}_tb1")
    tb2 = st.file_uploader(f"[{prog}] File trưng bày #2", type=["xlsx"], key=f"{prog}_tb2")

    st.markdown("**Upload 2 file DOANH SỐ (sheet phải trùng tên CT, ví dụ 'NMCD')**")
    ds1 = st.file_uploader(f"[{prog}] File doanh số #1", type=["xlsx"], key=f"{prog}_ds1")
    ds2 = st.file_uploader(f"[{prog}] File doanh số #2", type=["xlsx"], key=f"{prog}_ds2")

    data_key = f"__{prog}_data__"

    # Nút xử lý & lưu session
    if tb1 and tb2 and st.button(f"Xử lý CT {prog}", key=f"{prog}_process_btn"):
        try:
            df1 = read_display_excel(tb1)
            df2 = read_display_excel(tb2)
            result, m1, m2 = combine_two_months(df1, df2)

            if ds1:
                s1 = read_sales_excel(ds1, program_sheet_name=prog)
                result = result.merge(s1, on="Mã khách hàng", how="left")
                result[f"Doanh số - {m1}"] = result.pop("Tổng Doanh số").fillna(0)
            if ds2:
                s2 = read_sales_excel(ds2, program_sheet_name=prog)
                result = result.merge(s2, on="Mã khách hàng", how="left")
                if "Tổng Doanh số" in result.columns:
                    result[f"Doanh số - {m2}"] = result.pop("Tổng Doanh số").fillna(0)

            for c in [f"Doanh số - {m1}", f"Doanh số - {m2}"]:
                result[c] = pd.to_numeric(result[c], errors="coerce").fillna(0).astype(int)
                
            if prog == "KOS&XX":
                # Miền MB: 200k/slot, miền khác: 300k/slot
                result = apply_status_kosxx(result, m1, m2, min_mb=200_000, min_other=300_000)
            else:
                per_min = PER_SLOT_MIN.get(prog, 0)
                result = apply_status_generic(result, m1, m2, per_slot_min=per_min)

            st.session_state[data_key] = {"df": result, "m1": m1, "m2": m2}
            st.success("✅ Hoàn tất: đã ghép doanh số & tính trạng thái.")
        except Exception as e:
            st.error(f"Lỗi khi xử lý: {e}")

    # Hiển thị/lọc khi đã có dữ liệu
    if data_key in st.session_state:
        result = st.session_state[data_key]["df"].copy()
        m1 = st.session_state[data_key]["m1"]
        m2 = st.session_state[data_key]["m2"]

        with st.expander(f"🔎 Bộ lọc — {prog}", expanded=False):
            c1, c2, c3, c4 = st.columns([1,1,1,1])
            with c1:
                npp_codes = st.multiselect(
                    "Mã NPP",
                    options=sorted(result["Mã NPP"].dropna().unique()),
                    key=f"{prog}_npp_codes"
                )
            with c2:
                npp_names = st.multiselect(
                    "Tên NPP",
                    options=sorted(result["Tên NPP"].dropna().unique()),
                    key=f"{prog}_npp_names"
                )
            with c3:
                statuses = st.multiselect(
                    "Trạng thái",
                    options=["Đạt","Không Đạt","Không xét"],
                    key=f"{prog}_statuses"
                )
            with c4:
                kw = st.text_input("Tìm (Mã KH / Tên KH)", key=f"{prog}_kw")
        
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            min_sales_m1 = st.number_input(
                f"Doanh số tối thiểu – {m1}",
                min_value=0, value=0, step=50_000, key=f"{prog}_min_sales_m1"
            )
        with c6:
            min_sales_m2 = st.number_input(
                f"Doanh số tối thiểu – {m2}",
                min_value=0, value=0, step=50_000, key=f"{prog}_min_sales_m2"
            )
        with c7:
            min_slots_m1 = st.number_input(
                f"Giai đoạn (số suất) – {m1}",
                min_value=0, value=0, step=1, key=f"{prog}_min_slots_m1"
            )
        with c8:
            min_slots_m2 = st.number_input(
                f"Giai đoạn (số suất) – {m2}",
                min_value=0, value=0, step=1, key=f"{prog}_min_slots_m2"
            )

        # ================== Áp dụng lọc ==================
        filtered = result.copy()

        if npp_codes:
            filtered = filtered[filtered["Mã NPP"].isin(npp_codes)]
        if npp_names:
            filtered = filtered[filtered["Tên NPP"].isin(npp_names)]
        if statuses:
            filtered = filtered[filtered["TRẠNG THÁI"].isin(statuses)]
        if kw:
            kw_l = kw.strip().lower()
            filtered = filtered[
                filtered["Mã khách hàng"].astype(str).str.lower().str.contains(kw_l)
                | filtered["Tên khách hàng"].astype(str).str.lower().str.contains(kw_l)
            ]

        # Doanh số tối thiểu theo từng tháng
        filtered = filtered[
            (filtered[f"Doanh số - {m1}"].astype(int) >= int(min_sales_m1))
            & (filtered[f"Doanh số - {m2}"].astype(int) >= int(min_sales_m2))
        ]

        # Giai đoạn (số suất) tối thiểu theo từng tháng
        if int(min_slots_m1) > 0:
            filtered = filtered[filtered[f"Giai đoạn - {m1}"].astype(int) >= int(min_slots_m1)]
        if int(min_slots_m2) > 0:
            filtered = filtered[filtered[f"Giai đoạn - {m2}"].astype(int) >= int(min_slots_m2)]

        # ================== Hiển thị & Tải xuống ==================
        st.dataframe(filtered, use_container_width=True)

        # Excel sau khi lọc
        excel_filtered = export_excel_layout(filtered, m1, m2, prog)
        st.download_button(
            "⬇️ Tải EXCEL – Kết quả (Sau khi lọc)",
            data=excel_filtered,
            file_name=f"{prog}_ketqua_loc_{m1}_{m2}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{prog}_dl_filtered",
        )

        # Excel bản chuẩn (không lọc)
        excel_raw = export_excel_layout(result, m1, m2, prog)
        st.download_button(
            "⬇️ Tải EXCEL – Kết quả (Bản chuẩn)",
            data=excel_raw,
            file_name=f"{prog}_ketqua_chuan_{m1}_{m2}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{prog}_dl_raw",
        )
    else:
        st.info("👉 Upload file và bấm **Xử lý** để tạo dữ liệu trước khi lọc/tải.")

