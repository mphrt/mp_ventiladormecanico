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

def add_signature_inline(pdf_obj, canvas_result, x_target_center, y, max_w=65, max_h=20):
    """
    Dibuja la firma centrada en x_target_center.
    """
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w, img_h = img.size
        
        # Calcular escala manteniendo ratio
        ratio = min(max_w / img_w, max_h / img_h)
        final_w = img_w * ratio
        final_h = img_h * ratio
        
        # Calcular X para que el centro de la imagen coincida con x_target_center
        x_pos = x_target_center - (final_w / 2)
        
        pdf_obj.image(tmp_path, x=x_pos, y=y, w=final_w, h=final_h)
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
    pdf.set_text_color(0, 0, 0)
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
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", fs_head)
    pdf.cell(w, head_h, title, border=1, ln=1, align="L", fill=True)
    y_body = y + head_h
    x_text = x + padding
    w_text = max(1, w - 2 * padding)
    pdf.set_xy(x_text, y_body + padding)
    pdf.set_font("Arial", "", fs_body)
    if text:
        pdf.multi_cell(w_text, body_line_h, text, border=0, align="L")
    end_y = pdf.get_y()
    content_h = max(min_h, (end_y - (y_body + padding)) + padding)
    pdf.rect(x, y_body, w, content_h)
    pdf.set_y(y_body + content_h)

def draw_analisis_columns(pdf, x_start, y_start, col_w, data_list):
    row_h_field = 3.4
    label_w = 28.0
    text_w = col_w - label_w - 3.0
    TAB = "  " * 2
    def draw_column_no_lines(x, y, data):
        yy = y
        def field(lbl, val=""):
            nonlocal yy
            pdf.set_xy(x, yy)
            pdf.set_font("Arial", "", 6.2)
            pdf.cell(label_w, row_h_field, f"{TAB}{lbl}", border=0, ln=0)
            pdf.set_xy(x + label_w + 2, yy)
            pdf.cell(text_w, row_h_field, f": {val}", border=0, ln=1)
            yy += row_h_field
        field("EQUIPO", data.get("equipo", ""))
        field("MARCA", data.get("marca", ""))
        field("MODELO", data.get("modelo", ""))
        field("NÚMERO SERIE", data.get("serie", ""))
        return yy
    num_equipos = len(data_list)
    y_current = y_start
    if num_equipos == 1:
        draw_column_no_lines(x_start, y_current, data_list[0])
        y_current = pdf.get_y() + 2
    elif num_equipos >= 2:
        gap_cols = 6
        col_w2 = (col_w - gap_cols) / 2.0
        draw_column_no_lines(x_start, y_current, data_list[0])
        draw_column_no_lines(x_start + col_w2 + gap_cols, y_current, data_list[1])
        y_current = pdf.get_y() + 2
    return y_current

def main():
    st.title("Pauta de Mantenimiento Preventivo - Ventilador Mecánico")

    marca = st.text_input("MARCA")
    modelo = st.text_input("MODELO")
    sn = st.text_input("S/N")
    ideq = st.text_input("IDEQ")
    inventario = st.text_input("N/INVENTARIO")
    fecha = st.date_input("FECHA", value=datetime.date.today())
    ubicacion = st.text_input("UBICACIÓN")

    def checklist(title, items):
        st.subheader(title)
        respuestas = []
        for item in items:
            col1, col2 = st.columns([5, 3])
            with col1: st.markdown(item)
            with col2: seleccion = st.radio("", ["OK", "NO", "N/A"], horizontal=True, key=item)
            respuestas.append((item, seleccion))
        return respuestas

    chequeo_visual = checklist("1. Chequeo visual y comprobaciones", ["1.1. Válvula espiratoria", "1.2. Diafragma", "1.3. Filtro entrada de aire", "1.4. Chequeo de alarmas", "1.5. Panel frontal / pantalla touch", "1.6. Baterías de respaldo", "1.7. Mangueras de alta presión grado hospitalario", "1.8. Sensor/celda de oxígeno"])
    verif_param = checklist("2. Verificación de parámetros y funciones", ["2.1. Volumen", "2.2. Presiones", "2.3. Flujo", "2.4. FiO%", "2.5. Frecuencia", "2.6. Relación I:E"])
    seg_electrica = checklist("3. Mediciones seguridad eléctrica", ["3.1. Medición de corrientes de fuga normal condición", "3.2. Medición de corrientes de fuga con neutro abierto"])

    st.subheader("4. Instrumentos de análisis")
    if "analisis_equipos" not in st.session_state: st.session_state.analisis_equipos = [{}, {}]
    for i, _ in enumerate(st.session_state.analisis_equipos):
        st.markdown(f"**Equipo {i+1}**")
        st.session_state.analisis_equipos[i]["equipo"] = st.text_input("Equipo", key=f"equipo_{i}")
        st.session_state.analisis_equipos[i]["marca"] = st.text_input("Marca", key=f"marca_{i}")
        st.session_state.analisis_equipos[i]["modelo"] = st.text_input("Modelo", key=f"modelo_{i}")
        st.session_state.analisis_equipos[i]["serie"] = st.text_input("Número de Serie", key=f"serie_{i}")

    observaciones = st.text_area("Observaciones")
    observaciones_interno = st.text_area("Observaciones (uso interno)")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    col_tecnico, col_ingenieria, col_clinico = st.columns(3)
    with col_tecnico:
        st.write("Técnico Encargado:")
        canvas_result_tecnico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="canvas_tecnico")
    with col_ingenieria:
        st.write("Ingeniería Clínica:")
        canvas_result_ingenieria = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="canvas_ingenieria")
    with col_clinico:
        st.write("Personal Clínico:")
        canvas_result_clinico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, key="canvas_clinico")

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

        pdf.set_font("Arial", "B", 8)
        ideq_txt = f"IDEQ: {ideq}"
        ideq_w = pdf.get_string_width(ideq_txt) + 4
        pdf.set_fill_color(230, 230, 230)
        pdf.set_xy(page_w - SIDE_MARGIN - ideq_w, 4)
        pdf.cell(ideq_w, 4.5, ideq_txt, border=1, align="C", fill=True)

        pdf.set_font("Arial", "B", 7)
        pdf.set_xy(logo_x + LOGO_W_MM + 4, 12)
        pdf.cell(FIRST_TAB_RIGHT - (logo_x + LOGO_W_MM + 4), 5.0, "PAUTA MANTENCIÓN VENTILADOR MECÁNICO", border=1, align="C", fill=True)

        # ======= DATOS =======
        content_y_base = 19
        pdf.set_y(content_y_base)
        line_h = 3.4
        label_w = 35.0

        x_date = FIRST_TAB_RIGHT - 33.0
        pdf.set_xy(x_date - 15, content_y_base)
        pdf.set_font("Arial", "B", 7.5); pdf.cell(13, line_h, "FECHA:", 0, 0, "R")
        pdf.set_font("Arial", "", 7.5); pdf.set_xy(x_date, content_y_base)
        pdf.cell(11, line_h, f"{fecha.day:02d}", 1, 0, "C")
        pdf.cell(11, line_h, f"{fecha.month:02d}", 1, 0, "C")
        pdf.cell(11, line_h, f"{fecha.year:04d}", 1, 1, "C")

        def left_field(lbl, val):
            pdf.set_x(SIDE_MARGIN); pdf.set_font("Arial", "", 7.5)
            pdf.cell(label_w, line_h, lbl, 0, 0, "L")
            pdf.cell(2, line_h, ":", 0, 0, "C")
            pdf.cell(0, line_h, str(val), 0, 1, "L")

        left_field("MARCA", marca)
        left_field("MODELO", modelo)
        left_field("S/N", sn)
        left_field("N/INVENTARIO", inventario)
        left_field("UBICACIÓN", ubicacion)

        # ======= TABLAS =======
        pdf.ln(2.6); start_y_tables = pdf.get_y()
        ITEM_W = max(62.0, col_total_w - 36.0)
        create_checkbox_table(pdf, "1. Chequeo visual y comprobaciones", chequeo_visual, SIDE_MARGIN, ITEM_W, 12.0)
        create_checkbox_table(pdf, "2. Verificación de parámetros y funciones", verif_param, SIDE_MARGIN, ITEM_W, 12.0)
        create_checkbox_table(pdf, "3. Mediciones seguridad eléctrica", seg_electrica, SIDE_MARGIN, ITEM_W, 12.0)
        
        pdf.set_x(SIDE_MARGIN); pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 7.5)
        pdf.cell(col_total_w, 4.0, "    4. Instrumentos de análisis", border=1, ln=1, fill=True)
        draw_analisis_columns(pdf, SIDE_MARGIN, pdf.get_y()+1, col_total_w, st.session_state.analisis_equipos)

        # ======= COLUMNA DERECHA =======
        pdf.set_y(start_y_tables)
        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, 20, "Observaciones", observaciones)
        pdf.ln(2)
        draw_si_no_boxes(pdf, SECOND_COL_LEFT, pdf.get_y(), operativo, label_w=40)
        pdf.ln(2)
        
        # Firma Técnico (Centrada en su área)
        pdf.set_x(SECOND_COL_LEFT); pdf.set_font("Arial", "", 7.5)
        y_firma_txt = pdf.get_y()
        pdf.cell(0, 4.6, f"NOMBRE TÉCNICO/INGENIERO: {tecnico}", 0, 1)
        pdf.set_x(SECOND_COL_LEFT); pdf.cell(14, 4.6, "FIRMA:", 0, 0)
        # Centro de la columna derecha para la firma del técnico
        center_tecnico = SECOND_COL_LEFT + (col_total_w / 2)
        add_signature_inline(pdf, canvas_result_tecnico, center_tecnico, y_firma_txt + 4, 55, 18)
        
        pdf.set_y(y_firma_txt + 24)
        pdf.set_x(SECOND_COL_LEFT); pdf.cell(0, 4.0, f"EMPRESA RESPONSABLE: {empresa}", 0, 1)
        pdf.ln(2.0)
        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, 15, "Observaciones (uso interno)", observaciones_interno)

        # ======= RECEPCIÓN CONFORME (Centrado de firmas sobre líneas) =======
        pdf.ln(10); y_sigs = pdf.get_y()
        line_w = 45
        gap_between_lines = 10
        
        # Coordenadas X de inicio de las líneas
        x_line1 = SECOND_COL_LEFT
        x_line2 = SECOND_COL_LEFT + line_w + gap_between_lines
        
        # Dibujar líneas
        pdf.line(x_line1, y_sigs + 15, x_line1 + line_w, y_sigs + 15)
        pdf.line(x_line2, y_sigs + 15, x_line2 + line_w, y_sigs + 15)
        
        # Textos debajo de las líneas
        pdf.set_font("Arial", "B", 6.5)
        pdf.set_xy(x_line1, y_sigs + 16); pdf.multi_cell(line_w, 3.5, "RECEPCIÓN CONFORME\nINGENIERÍA CLÍNICA", 0, "C")
        pdf.set_xy(x_line2, y_sigs + 16); pdf.multi_cell(line_w, 3.5, "RECEPCIÓN CONFORME\nPERSONAL CLÍNICO", 0, "C")
        
        # Calcular centros de cada línea para las firmas
        center_sig1 = x_line1 + (line_w / 2)
        center_sig2 = x_line2 + (line_w / 2)
        
        # Añadir firmas centradas (y_sigs - altura_firma para que queden sobre la línea)
        add_signature_inline(pdf, canvas_result_ingenieria, center_sig1, y_sigs - 2, 35, 15)
        add_signature_inline(pdf, canvas_result_clinico, center_sig2, y_sigs - 2, 35, 15)

        out = pdf.output(dest="S")
        final_filename = f"{ideq}_MP_Ventilador_{sn}.pdf" if ideq else f"MP_Ventilador_{sn}.pdf"
        st.download_button("Descargar PDF", bytes(out), file_name=final_filename, mime="application/pdf")

if __name__ == "__main__":
    main()
