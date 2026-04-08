import streamlit as st
from fpdf import FPDF
import datetime
import io
import tempfile
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image

# ========= Pie de página =========
FOOTER_LINES = [
    "PAUTA MANTENIMIENTO PREVENTIVO VENTILADOR MECÁNICO (Ver 2)",
    "UNIDAD DE INGENIERÍA CLÍNICA",
    "HOSPITAL REGIONAL DE TALCA",
]

class PDF(FPDF):
    def __init__(self, *args, footer_lines=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._footer_lines = footer_lines or []

    def footer(self):
        if not self._footer_lines:
            return
        self.set_y(-15)
        y = self.get_y()
        subtitle_fs = 6.2
        line_h = 3.4
        first_line = self._footer_lines[0]
        self.set_font("Arial", "B", subtitle_fs)
        text_w = self.get_string_width(first_line)
        x_left = self.l_margin
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.2)
        self.line(x_left, y, x_left + text_w, y)
        self.ln(1.6)
        self.set_x(self.l_margin)
        self.cell(0, line_h, first_line, ln=1, align="L")
        self.set_font("Arial", "", subtitle_fs)
        for line in self._footer_lines[1:]:
            self.set_x(self.l_margin)
            self.cell(0, line_h, line, ln=1, align="L")

# ========= utilidades =========
def _crop_signature(canvas_result):
    if canvas_result.image_data is None:
        return None
    img_array = canvas_result.image_data.astype(np.uint8)
    img = Image.fromarray(img_array)
    gray_img = img.convert("L")
    threshold = 230
    coords = np.argwhere(np.array(gray_img) < threshold)
    if coords.size == 0:
        return None
    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)
    cropped_img = img.crop((min_x, min_y, max_x + 1, max_y + 1))
    if cropped_img.mode == "RGBA":
        cropped_img = cropped_img.convert("RGB")
    img_byte_arr = io.BytesIO()
    cropped_img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr

def add_signature_inline(pdf_obj, canvas_result, x, y, w_mm=65, h_mm=20):
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w = w_mm
        img_h = (img.height / img.width) * img_w
        if img_h > h_mm:
            img_h = h_mm
            img_w = (img.width / img.height) * img_h
        pdf_obj.image(tmp_path, x=x, y=y, w=img_w, h=img_h)
    except Exception as e:
        st.error(f"Error al añadir imagen: {e}")

def draw_si_no_boxes(pdf, x, y, selected, size=4.5, gap=4, text_gap=1.5, label_w=36):
    pdf.set_font("Arial", "", 7.5)
    pdf.set_xy(x, y)
    pdf.cell(label_w, size, "EQUIPO OPERATIVO:", 0, 0)
    x_box_si = x + label_w + 2
    pdf.rect(x_box_si, y, size, size)
    pdf.set_xy(x_box_si, y)
    pdf.cell(size, size, "X" if selected == "SI" else "", 0, 0, "C")
    pdf.set_xy(x_box_si + size + text_gap, y)
    pdf.cell(6, size, "SI", 0, 0)
    x_box_no = x_box_si + size + text_gap + 6 + gap
    pdf.rect(x_box_no, y, size, size)
    pdf.set_xy(x_box_no, y)
    pdf.cell(size, size, "X" if selected == "NO" else "", 0, 0, "C")
    pdf.set_xy(x_box_no + size + text_gap, y)
    pdf.cell(6, size, "NO", 0, 1)

def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w, row_h=3.4, head_fs=7.2, cell_fs=6.2, indent_w=5.0, title_tab_spaces=2):
    title_prefix = " " * (title_tab_spaces * 2)
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", head_fs)
    pdf.cell(item_w, row_h, f"{title_prefix}{section_title}", border=1, ln=0, align="L", fill=True)
    pdf.set_font("Arial", "B", cell_fs)
    pdf.cell(col_w, row_h, "OK", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", cell_fs)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(indent_w, row_h, "", border=0, ln=0)
        pdf.cell(max(1, item_w - indent_w), row_h, item, border=0, ln=0, align="L")
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, ln=1, align="C")
    pdf.ln(1.6)

def draw_boxed_text_auto(pdf, x, y, w, min_h, title, text, head_h=4.6, fs_head=7.2, fs_body=7.0, body_line_h=3.2, padding=1.2):
    pdf.set_xy(x, y)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", fs_head)
    pdf.cell(w, head_h, title, border=1, ln=1, align="L", fill=True)
    y_body = y + head_h
    pdf.set_xy(x + padding, y_body + padding)
    pdf.set_font("Arial", "", fs_body)
    if text:
        pdf.multi_cell(w - 2*padding, body_line_h, text, border=0, align="L")
    end_y = pdf.get_y()
    content_h = max(min_h, (end_y - (y_body + padding)) + padding)
    pdf.rect(x, y_body, w, content_h)
    pdf.set_y(y_body + content_h)

def draw_analisis_columns(pdf, x_start, y_start, col_w, data_list):
    row_h_field = 3.4
    label_w = 28.0
    TAB = "    "
    def draw_column_no_lines(x, y, data):
        yy = y
        def field(lbl, val=""):
            nonlocal yy
            pdf.set_xy(x, yy)
            pdf.set_font("Arial", "", 6.2)
            pdf.cell(label_w, row_h_field, f"{TAB}{lbl}", border=0, ln=0)
            pdf.set_xy(x + label_w + 2, yy)
            pdf.cell(col_w - label_w - 5, row_h_field, f": {val}", border=0, ln=1)
            yy += row_h_field
        field("EQUIPO", data.get("equipo", ""))
        field("MARCA", data.get("marca", ""))
        field("MODELO", data.get("modelo", ""))
        field("NÚMERO SERIE", data.get("serie", ""))
        return yy
    y_current = y_start
    if len(data_list) > 0:
        draw_column_no_lines(x_start, y_current, data_list[0])
        if len(data_list) > 1:
            draw_column_no_lines(x_start + (col_w/2) + 3, y_current, data_list[1])
        y_current = pdf.get_y() + 2
    return y_current

# ========= app =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Ventilador Mecánico")

    ideq = st.text_input("IDEQ") # --- CAMBIO: Se agregó entrada IDEQ ---
    marca = st.text_input("MARCA")
    modelo = st.text_input("MODELO")
    sn = st.text_input("S/N")
    inventario = st.text_input("N/INVENTARIO")
    fecha = st.date_input("FECHA", value=datetime.date.today())
    ubicacion = st.text_input("UBICACIÓN")

    # Checklist Secciones
    chequeo_visual = checklist("1. Chequeo visual y comprobaciones", ["1.1. Válvula espiratoria", "1.2. Diafragma", "1.3. Filtro entrada de aire", "1.4. Chequeo de alarmas", "1.5. Panel frontal / pantalla touch", "1.6. Baterías de respaldo", "1.7. Mangueras de alta presión hospitalaria", "1.8. Sensor/celda de oxígeno"])
    verif_param = checklist("2. Verificación de parámetros y funciones", ["2.1. Volumen", "2.2. Presiones", "2.3. Flujo", "2.4. FiO%", "2.5. Frecuencia", "2.6. Relación I:E"])
    seg_electrica = checklist("3. Mediciones seguridad eléctrica", ["3.1. Medición de corrientes de fuga normal", "3.2. Medición de corrientes de fuga neutro abierto"])

    # Instrumentos de Análisis
    st.subheader("4. Instrumentos de análisis")
    if "analisis_equipos" not in st.session_state: st.session_state.analisis_equipos = [{}, {}]
    for i, _ in enumerate(st.session_state.analisis_equipos):
        st.markdown(f"**Equipo {i+1}**")
        st.session_state.analisis_equipos[i]["equipo"] = st.text_input("Equipo", key=f"eq_{i}")
        st.session_state.analisis_equipos[i]["marca"] = st.text_input("Marca", key=f"ma_{i}")
        st.session_state.analisis_equipos[i]["modelo"] = st.text_input("Modelo", key=f"mo_{i}")
        st.session_state.analisis_equipos[i]["serie"] = st.text_input("Serie", key=f"se_{i}")

    observaciones = st.text_area("Observaciones")
    observaciones_interno = st.text_area("Observaciones (uso interno)")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    c1, c2, c3 = st.columns(3)
    with c1: canvas_tecnico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="c_tec")
    with c2: canvas_ingenieria = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="c_ing")
    with c3: canvas_clinico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="c_cli")

    if st.button("Generar PDF"):
        SIDE_MARGIN, TOP_MARGIN = 9, 4
        pdf = PDF("L", "mm", "A4", footer_lines=FOOTER_LINES)
        pdf.set_margins(SIDE_MARGIN, TOP_MARGIN, SIDE_MARGIN)
        pdf.add_page()
        
        page_w = pdf.w
        usable_w = page_w - 2 * SIDE_MARGIN
        col_total_w = (usable_w - 6) / 2.0
        FIRST_TAB_RIGHT = SIDE_MARGIN + col_total_w
        SECOND_COL_LEFT = FIRST_TAB_RIGHT + 6

        # ======= ENCABEZADO =======
        logo_x, logo_y, LOGO_W_MM = 2, 2, 60
        try: pdf.image("logo_hrt_final.jpg", x=logo_x, y=logo_y, w=LOGO_W_MM)
        except: pass

        # --- IDEQ (Igual que en el código de arriba) ---
        pdf.set_font("Arial", "B", 8)
        ideq_txt = f"IDEQ: {ideq}"
        ideq_w = pdf.get_string_width(ideq_txt) + 4
        pdf.set_fill_color(230, 230, 230)
        pdf.set_xy(page_w - SIDE_MARGIN - ideq_w, 4)
        pdf.cell(ideq_w, 4.5, ideq_txt, border=1, align="C", fill=True)

        # TÍTULO
        pdf.set_font("Arial", "B", 7)
        pdf.set_xy(logo_x + LOGO_W_MM + 4, 12)
        pdf.cell(FIRST_TAB_RIGHT - (logo_x + LOGO_W_MM + 4), 5.0, "PAUTA MANTENCIÓN VENTILADOR MECÁNICO", border=1, align="C", fill=True)

        content_y_base = 19
        pdf.set_y(content_y_base)

        # ======= FECHA =======
        line_h = 3.4
        x_date = FIRST_TAB_RIGHT - 33.0
        pdf.set_xy(x_date - 15, content_y_base)
        pdf.set_font("Arial", "B", 7.5)
        pdf.cell(13, line_h, "FECHA:", 0, 0, "R")
        pdf.set_font("Arial", "", 7.5)
        pdf.set_xy(x_date, content_y_base)
        pdf.cell(11, line_h, f"{fecha.day:02d}", 1, 0, "C")
        pdf.cell(11, line_h, f"{fecha.month:02d}", 1, 0, "C")
        pdf.cell(11, line_h, f"{fecha.year:04d}", 1, 1, "C")

        # ======= DATOS (Sin negrita en valores) =======
        label_w = 35.0
        def field(lbl, val):
            pdf.set_x(SIDE_MARGIN); pdf.set_font("Arial", "", 7.5)
            pdf.cell(label_w, line_h, lbl, 0, 0, "L")
            pdf.cell(2, line_h, ":", 0, 0, "C")
            pdf.cell(0, line_h, str(val), 0, 1, "L")

        field("MARCA", marca)
        field("MODELO", modelo)
        field("S/N", sn)
        field("N/INVENTARIO", inventario)
        field("UBICACIÓN", ubicacion)

        # ======= TABLAS =======
        pdf.ln(2)
        start_y_tables = pdf.get_y()
        create_checkbox_table(pdf, "1. Chequeo visual", chequeo_visual, SIDE_MARGIN, col_total_w - 36, 12)
        create_checkbox_table(pdf, "2. Parámetros", verif_param, SIDE_MARGIN, col_total_w - 36, 12)
        create_checkbox_table(pdf, "3. Seg. Eléctrica", seg_electrica, SIDE_MARGIN, col_total_w - 36, 12)
        
        # Análisis
        pdf.set_x(SIDE_MARGIN); pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.5)
        pdf.cell(col_total_w, 4.0, "    4. Instrumentos de análisis", border=1, ln=1, fill=True)
        draw_analisis_columns(pdf, SIDE_MARGIN, pdf.get_y()+1, col_total_w, st.session_state.analisis_equipos)

        # ======= COLUMNA DERECHA =======
        pdf.set_y(start_y_tables)
        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, 15, "Observaciones", observaciones)
        pdf.ln(2)
        draw_si_no_boxes(pdf, SECOND_COL_LEFT, pdf.get_y(), operativo, label_w=40)
        pdf.ln(2)
        
        # Firma Técnico
        pdf.set_x(SECOND_COL_LEFT); pdf.set_font("Arial", "", 7.5)
        pdf.cell(0, 4, f"NOMBRE TÉCNICO: {tecnico}", 0, 1)
        pdf.set_x(SECOND_COL_LEFT); pdf.cell(14, 4, "FIRMA:", 0, 1)
        y_sig = pdf.get_y()
        add_signature_inline(pdf, canvas_tecnico, SECOND_COL_LEFT + 20, y_sig, 50, 15)
        
        pdf.set_y(y_sig + 18)
        pdf.set_x(SECOND_COL_LEFT); pdf.cell(0, 4, f"EMPRESA RESPONSABLE: {empresa}", 0, 1)
        pdf.ln(2)
        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, 12, "Uso Interno", observaciones_interno)

        # Firmas Inferiores
        pdf.ln(15); y_f = pdf.get_y()
        pdf.line(SECOND_COL_LEFT, y_f, SECOND_COL_LEFT + 45, y_f)
        pdf.line(SECOND_COL_LEFT + 55, y_f, SECOND_COL_LEFT + 100, y_f)
        pdf.set_font("Arial", "B", 6)
        pdf.set_xy(SECOND_COL_LEFT, y_f + 1); pdf.multi_cell(45, 3, "INGENIERÍA CLÍNICA", 0, "C")
        pdf.set_xy(SECOND_COL_LEFT + 55, y_f + 1); pdf.multi_cell(45, 3, "PERSONAL CLÍNICO", 0, "C")

        out = pdf.output(dest="S")
        st.download_button("Descargar PDF", bytes(out), file_name=f"MP_Ventilador_{sn}.pdf", mime="application/pdf")

def checklist(title, items):
    st.subheader(title)
    res = []
    for i in items:
        c1, c2 = st.columns([2, 1])
        with c1: st.write(i)
        with c2: sel = st.radio("", ["OK", "NO", "N/A"], horizontal=True, key=i)
        res.append((i, sel))
    return res

if __name__ == "__main__":
    main()
