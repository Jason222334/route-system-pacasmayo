import warnings
warnings.filterwarnings("ignore")
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
from datetime import datetime, timedelta
from supabase import create_client, Client
from fpdf import FPDF
import io

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Optimizador de Rutas - Pacasmayo", page_icon="🚚", layout="wide")
PACASMAYO_COORDS = {"lat": -7.4002, "lng": -79.5717}

# ---------------- CONEXIÓN SUPABASE ----------------
class SupabaseManager:
    def __init__(self):
        self.url = st.secrets["SUPABASE_URL"]
        self.key = st.secrets["SUPABASE_KEY"]
        self.client: Client = create_client(self.url, self.key)

    def get(self, table):
        return self.client.table(table).select("*").execute().data

    def insert(self, table, data):
        return self.client.table(table).insert(data).execute().data

    def update(self, table, data, eq_field, eq_value):
        return self.client.table(table).update(data).eq(eq_field, eq_value).execute().data

# ---------------- PDF ----------------
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Reporte de Eficiencia - Pacasmayo', 0, 1, 'C')
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    # Método genérico ya existente en tu código:
    def chapter(self, title, body):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, title, 0, 1)
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 8, body)
        self.ln(5)

    # 👇 Nuevos métodos-helpers para mantener compatibilidad
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, title, 0, 1)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 8, body)
        self.ln(3)

# ---------------- MAIN ----------------
def main():
    sb = SupabaseManager()
    st.title("🚚 Sistema Optimizador de Rutas - Pacasmayo")
    st.sidebar.title("Menú")
    option = st.sidebar.radio(
        "Selecciona una sección",
        ["Dashboard","Gestión de Entregas", "Optimización de Rutas","Gestión de Vehículos","Gestión de Almacenes","Reportes"]
    )

    if option == "Dashboard":
        show_dashboard(sb)
    elif option == "Gestión de Entregas":
        manage_deliveries(sb)
    elif option == "Optimización de Rutas":
        optimize_routes(sb)
    elif option == "Gestión de Vehículos":
        show_vehicle_management(sb)
    elif option == "Gestión de Almacenes":
        show_depot_management(sb)
    elif option == "Reportes":
        generate_reports(sb)


# ---------------- DASHBOARD ----------------

def show_dashboard(sb: SupabaseManager):
    st.header("📊 Dashboard General - Pacasmayo")

    deliveries = sb.get("deliveries")
    vehicles = sb.get("vehicles")
    drivers = sb.get("drivers")
    routes = sb.get("optimized_routes")

    if not deliveries and not routes:
        st.info("No hay datos aún para mostrar estadísticas.")
        return

    # --- MÉTRICAS PRINCIPALES ---
    total_deliveries = len(deliveries)
    completed = len([d for d in deliveries if d["status"] == "delivered"])
    in_progress = len([d for d in deliveries if d["status"] == "in_progress"])
    pending = len([d for d in deliveries if d["status"] == "pending"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Entregas", total_deliveries)
    col2.metric("✅ Entregadas", completed)
    col3.metric("🚚 En Progreso", in_progress)
    col4.metric("🕓 Pendientes", pending)

    # --- GRÁFICO 1: ESTADOS DE ENTREGA ---
    if deliveries:
        df = pd.DataFrame(deliveries)
        if "status" in df.columns:
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["Estado", "Cantidad"]
            fig_status = px.pie(
                status_counts, names="Estado", values="Cantidad",
                title="Distribución de Estados de Entrega",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_status, use_container_width=True)

    # --- GRÁFICO 3: HISTOGRAMA DE DISTANCIAS OPTIMIZADAS ---
    if routes:
        df_routes = pd.DataFrame(routes)
        if "total_distance_km" in df_routes.columns:
            fig_dist = px.histogram(
                df_routes, x="total_distance_km", nbins=10,
                title="Distribución de Distancias de Rutas (km)",
                color_discrete_sequence=["#3E92CC"]
            )
            st.plotly_chart(fig_dist, use_container_width=True)

    # --- MAPA DE ENTREGAS ---
    st.subheader("🌍 Mapa de Entregas en Pacasmayo")
    coords = []
    for d in deliveries:
        if d.get("customer_coordinates"):
            coords.append({
                "lat": d["customer_coordinates"]["lat"],
                "lon": d["customer_coordinates"]["lng"],
                "Estado": d["status"],
                "Cliente": d["customer_name"]
            })
    if coords:
        df_coords = pd.DataFrame(coords)
        fig_map = px.scatter_mapbox(
            df_coords,
            lat="lat", lon="lon", color="Estado",
            hover_name="Cliente", zoom=14,
            center={"lat": -7.4002, "lon": -79.5717},
            mapbox_style="open-street-map",
            title="Ubicaciones de Entregas - Pacasmayo"
        )
        st.plotly_chart(fig_map, use_container_width=True)

    # --- KPI DE TIEMPO PROMEDIO Y DISTANCIA PROMEDIO ---
    if routes:
        avg_dist = round(df_routes["total_distance_km"].mean(), 2)
        avg_dur = round(df_routes["estimated_duration_minutes"].mean(), 2)
        col1, col2 = st.columns(2)
        col1.metric("📏 Distancia Promedio por Ruta (km)", avg_dist)
        col2.metric("⏱️ Duración Promedio (min)", avg_dur)


# ---------------- GESTIÓN DE ENTREGAS ----------------
def manage_deliveries(sb: SupabaseManager):
    st.header("📦 Gestión de Entregas en Pacasmayo")

    # --- Formulario para nueva entrega ---
    with st.form("nueva_entrega"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nombre del Cliente")
            phone = st.text_input("Teléfono")
            address = st.text_area("Dirección Completa (Ej. Jr. Dos de Mayo 135, Pacasmayo)")
        with col2:
            desc = st.text_area("Descripción del Paquete")
            weight = st.number_input("Peso (kg)", min_value=0.1)
            date = st.date_input("Fecha Estimada de Entrega")

        submitted = st.form_submit_button("Crear Entrega")
        if submitted:
            if name and address:
                coords = get_coordinates(address)
                if coords:
                    data = {
                        "tracking_number": f"TRK{int(datetime.now().timestamp())}",
                        "customer_name": name,
                        "customer_phone": phone,
                        "customer_address": address,
                        "customer_coordinates": coords,
                        "package_description": desc,
                        "package_weight": weight,
                        "status": "pending",
                        "estimated_delivery_time": date.isoformat()
                    }
                    sb.insert("deliveries", data)
                    st.success("✅ Entrega creada con coordenadas reales.")
                    st.rerun()
                else:
                    st.error("❌ No se pudo obtener coordenadas. Verifica la dirección.")
            else:
                st.warning("⚠️ Completa todos los campos obligatorios.")

    # --- Tabla de entregas ---
    st.subheader("📋 Lista de Entregas")
    deliveries = sb.get("deliveries")
    if not deliveries:
        st.info("No hay entregas registradas todavía.")
        return

    df = pd.DataFrame(deliveries)
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Filtrar por estado", ["Todos"] + sorted(df["status"].unique().tolist()))
    with col2:
        search = st.text_input("Buscar por cliente o tracking")

    if status_filter != "Todos":
        df = df[df["status"] == status_filter]
    if search:
        mask = df["customer_name"].str.contains(search, case=False) | df["tracking_number"].str.contains(search, case=False)
        df = df[mask]

    st.dataframe(df[["tracking_number", "customer_name", "status", "customer_address"]], use_container_width=True)

    # --- Acciones rápidas ---
    st.subheader("⚙️ Acciones Rápidas")
    if not df.empty:
        selected = st.selectbox("Selecciona una entrega:", df["tracking_number"].tolist())
        col1, col2, col3 = st.columns(3)
        if col1.button("📋 Pendiente"):
            sb.update("deliveries", {"status": "pending"}, "tracking_number", selected)
            st.success("Estado cambiado a Pendiente.")
            st.rerun()
        if col2.button("🚚 En Progreso"):
            sb.update("deliveries", {"status": "in_progress"}, "tracking_number", selected)
            st.success("Estado cambiado a En Progreso.")
            st.rerun()
        if col3.button("✅ Entregada"):
            sb.update("deliveries", {"status": "delivered"}, "tracking_number", selected)
            st.success("Estado cambiado a Entregada.")
            st.rerun()

# ---------------- OPTIMIZACIÓN DE RUTAS ----------------
def optimize_routes(sb: SupabaseManager):
    st.header("🗺️ Optimización de Rutas con Almacén (Google Maps + n8n)")
    
    # --- Selección de entregas pendientes ---
    deliveries = sb.get("deliveries")
    pending = [d for d in deliveries if d["status"] in ["pending", "in_progress"]]
    if not pending:
        st.info("📭 No hay entregas pendientes para optimizar.")
        return

    selected = st.multiselect(
        "Selecciona entregas:",
        [f"{d['tracking_number']} - {d['customer_name']}" for d in pending]
    )
    if len(selected) < 2:
        st.warning("Selecciona al menos dos entregas para optimizar una ruta.")
        return

    # --- Dirección del almacén (origen y destino) ---
    st.subheader("🏭 Selección de Almacén")

    depots = sb.get("depots")
    default_depot = next((d for d in depots if d["is_default"]), None)

    if not depots:
        st.warning("⚠️ No hay almacenes registrados. Agrega uno en 'Gestión de Almacenes'.")
        return

    selected_name = st.selectbox(
        "Selecciona el almacén de origen y destino:",
        [d["name"] for d in depots],
        index=depots.index(default_depot) if default_depot else 0
    )

    selected_depot = next(d for d in depots if d["name"] == selected_name)
    depot = selected_depot["coordinates"]
    st.info(f"📍 Usando almacén: **{selected_depot['name']}**, Dirección: {selected_depot['address']}")


    if not depot:
        st.warning("⚠️ No se pudo obtener coordenadas del almacén. Verifica la dirección.")

    # --- Botón para optimizar ---
    if st.button("🚀 Optimizar Ruta con n8n"):
        ids = [
            d["id"]
            for d in pending
            if f"{d['tracking_number']} - {d['customer_name']}" in selected
        ]
        try:
            payload = {"deliveries": ids}
            if depot:
                payload["depot"] = depot

            res = requests.post(
                st.secrets["N8N_WEBHOOK_URL"], json=payload, timeout=45
            )

            if res.status_code == 200:
                result = res.json()
                st.success("✅ Ruta optimizada correctamente.")

                # --- Mostrar métricas ---
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📏 Distancia total (km)", round(result["total_distance_km"], 2))
                with col2:
                    st.metric("⏱️ Duración estimada (min)", result["estimated_duration_minutes"])

                # --- Dibujar mapa ---
                if "optimized_sequence" in result and "encodedPolyline" in result["optimized_sequence"]:
                    encoded_poly = result["optimized_sequence"]["encodedPolyline"]
                    coords = decode_polyline(encoded_poly)
                    df_map = pd.DataFrame(coords)

                    fig = px.line_mapbox(
                        df_map,
                        lat="lat", lon="lon",
                        hover_name=df_map.index.astype(str),
                        zoom=14,
                        center={"lat": df_map["lat"].mean(), "lon": df_map["lon"].mean()},
                        title="🗺️ Ruta Optimizada - Pacasmayo"
                    )

                    # --- Almacén (inicio/fin) ---
                    if depot:
                        fig.add_scattermapbox(
                            lat=[depot["lat"]],
                            lon=[depot["lng"]],
                            mode="markers+text",
                            marker=dict(size=18, color="blue"),
                            text=["Almacén"],
                            textposition="top right",
                            name="Almacén"
                        )

                    # --- Entregas ordenadas ---
                    ordered = result["optimized_sequence"].get("ordered_waypoints", [])
                    if ordered:
                        fig.add_scattermapbox(
                            lat=[w["lat"] for w in ordered],
                            lon=[w["lng"] for w in ordered],
                            mode="markers+text",
                            marker=dict(size=12, color="orange"),
                            text=[f'{i+1}. {w.get("label","Entrega")}' for i, w in enumerate(ordered)],
                            textposition="top center",
                            name="Entregas"
                        )

                    fig.update_layout(mapbox_style="open-street-map")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ No se recibió una polilínea válida desde n8n.")
            else:
                st.error(f"❌ Error al optimizar ruta: {res.text}")

        except Exception as e:
            st.error(f"⚠️ Error al conectar con n8n: {e}")



def show_vehicle_management(sb: SupabaseManager):
    st.header("🚛 Gestión de Vehículos (CLAER)")

    # ---------------- CREAR ----------------
    with st.expander("➕ Registrar nuevo vehículo"):
        with st.form("form_nuevo_vehiculo"):
            col1, col2, col3 = st.columns(3)
            with col1:
                license_plate = st.text_input("Placa del vehículo")
            with col2:
                vehicle_type = st.selectbox("Tipo de vehículo", ["Camión Pequeño", "Camión Mediano", "Camión Grande", "Motocicleta"])
            with col3:
                capacity_kg = st.number_input("Capacidad (kg)", min_value=0.0, step=50.0)
            submitted = st.form_submit_button("Registrar")
            if submitted:
                if license_plate:
                    data = {
                        "license_plate": license_plate.strip().upper(),
                        "vehicle_type": vehicle_type,
                        "capacity_kg": capacity_kg
                    }
                    sb.client.table("vehicles").insert(data).execute()
                    st.success(f"✅ Vehículo {license_plate} registrado correctamente.")
                    st.rerun()
                else:
                    st.warning("⚠️ Debes ingresar una placa válida.")

    # ---------------- LEER ----------------
    st.subheader("📋 Lista de Vehículos")
    vehicles = sb.get("vehicles")
    if not vehicles:
        st.info("No hay vehículos registrados todavía.")
        return

    df = pd.DataFrame(vehicles)
    st.dataframe(df[["license_plate", "vehicle_type", "capacity_kg", "status", "created_at"]], use_container_width=True)

    # ---------------- ACTUALIZAR ----------------
    with st.expander("✏️ Actualizar información de un vehículo"):
        veh_ids = {v["license_plate"]: v["id"] for v in vehicles}
        selected = st.selectbox("Seleccionar vehículo", list(veh_ids.keys()))
        new_status = st.selectbox("Nuevo estado", ["available", "in_use", "maintenance"])
        if st.button("Actualizar Estado"):
            sb.client.table("vehicles").update({"status": new_status}).eq("id", veh_ids[selected]).execute()
            st.success(f"🔄 Estado de {selected} actualizado a '{new_status}'.")
            st.rerun()

    # ---------------- ELIMINAR ----------------
    with st.expander("🗑️ Eliminar vehículo"):
        veh_ids = {v["license_plate"]: v["id"] for v in vehicles}
        selected_del = st.selectbox("Seleccionar vehículo a eliminar", list(veh_ids.keys()))
        if st.button("Eliminar definitivamente"):
            sb.client.table("vehicles").delete().eq("id", veh_ids[selected_del]).execute()
            st.warning(f"🚫 Vehículo {selected_del} eliminado del registro.")
            st.rerun()

    # ---------------- REPORTE ----------------
    st.subheader("📄 Reporte de Vehículos en PDF")

    if st.button("📥 Generar PDF"):
        vehicles = sb.get("vehicles")
        if not vehicles:
            st.warning("No hay vehículos registrados.")
        else:
            # --- Crear PDF formal en tabla ---
            pdf = PDFReport()
            pdf.add_page()

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "REPORTE DE VEHÍCULOS - PACASMAYO", 0, 1, "C")
            pdf.ln(5)

            # Encabezados de tabla
            pdf.set_font("Arial", "B", 11)
            col_widths = [40, 45, 45, 35, 30]  # Placa, Tipo, Capacidad, Estado, Fecha
            headers = ["Placa", "Tipo de Vehículo", "Capacidad (kg)", "Estado", "Fecha"]

            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, 1, 0, "C")
            pdf.ln()

            # Filas de tabla
            pdf.set_font("Arial", "", 10)
            for v in vehicles:
                pdf.cell(col_widths[0], 8, str(v["license_plate"]), 1)
                pdf.cell(col_widths[1], 8, str(v["vehicle_type"])[:22], 1)
                pdf.cell(col_widths[2], 8, f"{v['capacity_kg']:.1f}", 1, 0, "C")
                pdf.cell(col_widths[3], 8, str(v["status"]), 1, 0, "C")
                fecha = str(v.get("created_at", ""))[:10]
                pdf.cell(col_widths[4], 8, fecha, 1, 1, "C")

            # Espaciado y resumen
            pdf.ln(8)
            pdf.set_font("Arial", "I", 9)
            pdf.cell(0, 8, f"Total de vehículos registrados: {len(vehicles)}", 0, 1, "L")
            pdf.cell(0, 8, "Reporte generado automáticamente por el sistema de rutas Pacasmayo.", 0, 1, "C")

            # Exportar PDF correctamente (solo una vez)
            pdf_output = pdf.output(dest="S")
            pdf_bytes = pdf_output.encode("latin1") if isinstance(pdf_output, str) else bytes(pdf_output)
            buf = io.BytesIO(pdf_bytes)

            st.download_button(
                "⬇️ Descargar PDF",
                buf,
                "reporte_vehiculos.pdf",
                "application/pdf"
            )

# ---------------- REPORTES ----------------
def generate_reports(sb: SupabaseManager):
    st.header("📄 Reportes de Eficiencia de Rutas en Pacasmayo")

    routes = sb.get("optimized_routes")
    if not routes:
        st.info("Aún no hay rutas optimizadas registradas.")
        return

    df = pd.DataFrame(routes)
    st.dataframe(df[["route_name", "total_distance_km", "estimated_duration_minutes"]])

    # Calcular métricas generales
    total_routes = len(df)
    total_distance = round(df["total_distance_km"].sum(), 2)
    avg_distance = round(df["total_distance_km"].mean(), 2)
    avg_duration = round(df["estimated_duration_minutes"].mean(), 2)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Rutas", total_routes)
    col2.metric("Distancia Total (km)", total_distance)
    col3.metric("Distancia Promedio (km)", avg_distance)
    col4.metric("Duración Promedio (min)", avg_duration)

    if st.button("📥 Generar PDF Detallado"):
        pdf = PDFReport()
        pdf.add_page()

        # ---------------- ENCABEZADO ----------------
        pdf.chapter("Resumen General", 
            f"Rutas generadas: {total_routes}\n"
            f"Distancia total: {total_distance} km\n"
            f"Distancia promedio: {avg_distance} km\n"
            f"Duración promedio: {avg_duration} minutos"
        )

        # ---------------- TABLA CENTRADA ----------------
        pdf.set_font('Arial', 'B', 11)
        col_widths = [80, 40, 40]  # Anchos de columnas (ajustados)
        table_width = sum(col_widths)
        page_width = pdf.w - 20  # márgenes izquierdo y derecho
        x_offset = (page_width - table_width) / 2

        pdf.set_x(x_offset)
        pdf.cell(col_widths[0], 8, "Nombre de Ruta", 1, 0, 'C')
        pdf.cell(col_widths[1], 8, "Distancia (km)", 1, 0, 'C')
        pdf.cell(col_widths[2], 8, "Duración (min)", 1, 1, 'C')

        pdf.set_font('Arial', '', 10)
        for _, row in df.iterrows():
            route_name = str(row["route_name"])[:35] + "..." if len(str(row["route_name"])) > 38 else str(row["route_name"])
            pdf.set_x(x_offset)
            pdf.cell(col_widths[0], 8, route_name, 1, 0)
            pdf.cell(col_widths[1], 8, f"{row['total_distance_km']:.2f}", 1, 0, 'C')
            pdf.cell(col_widths[2], 8, str(row["estimated_duration_minutes"]), 1, 1, 'C')

        # ---------------- PIE DE PÁGINA ----------------
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 9)
        pdf.cell(0, 10, "Reporte generado automáticamente por el sistema de optimización de rutas Pacasmayo.", 0, 1, 'C')

        # ---------------- DESCARGA ----------------
        pdf_output = pdf.output(dest="S")
        pdf_bytes = pdf_output.encode("latin1") if isinstance(pdf_output, str) else bytes(pdf_output)
        buf = io.BytesIO(pdf_bytes)
        st.download_button(
            "⬇️ Descargar PDF Detallado",
            buf,
            "reporte_detallado_pacasmayo.pdf",
            "application/pdf"
        )

# ---------------- FUNCIONES AUXILIARES ----------------
def get_coordinates(address):
    api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address},Pacasmayo,Peru&key={api_key}"
    r = requests.get(url)
    if r.status_code == 200:
        res = r.json()
        if res["results"]:
            loc = res["results"][0]["geometry"]["location"]
            return {"lat": loc["lat"], "lng": loc["lng"]}
    return None

import polyline

def decode_polyline(encoded_poly):
    """Convierte una polilínea codificada de Google en lista de coordenadas."""
    coords = polyline.decode(encoded_poly)
    return [{"lat": lat, "lon": lon} for lat, lon in coords]

def geocode_address(address):
    """Devuelve lat/lng reales de una dirección en Pacasmayo usando la API de Google."""
    api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address},Pacasmayo,Peru&key={api_key}"
    r = requests.get(url, timeout=20)
    if r.ok:
        data = r.json()
        if data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return {"address": address, "lat": loc["lat"], "lng": loc["lng"]}
    return None
def geocode_address(address):
    """Devuelve lat/lng reales de una dirección en Pacasmayo usando la API de Google."""
    api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address},Pacasmayo,Peru&key={api_key}"
    r = requests.get(url, timeout=20)
    if r.ok:
        data = r.json()
        if data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return {"address": address, "lat": loc["lat"], "lng": loc["lng"]}
    return None

def show_depot_management(sb: SupabaseManager):
    st.header("🏭 Gestión de Almacenes (Depots)")

    # ---------- CREAR NUEVO ALMACÉN ----------
    with st.expander("➕ Registrar nuevo almacén"):
        with st.form("form_nuevo_almacen"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nombre del Almacén (Ej. Principal, Secundario)")
                address = st.text_input("Dirección completa (Ej. Jr. Dos de Mayo 135, Pacasmayo)")
            with col2:
                is_default = st.checkbox("Marcar como predeterminado")
            submitted = st.form_submit_button("Registrar")
            if submitted:
                if name and address:
                    coords = geocode_address(address)
                    if coords:
                        data = {
                            "name": name,
                            "address": address,
                            "coordinates": {"lat": coords["lat"], "lng": coords["lng"]},
                            "is_default": is_default
                        }
                        # Si se marca como predeterminado, desmarcar otros
                        if is_default:
                            sb.client.table("depots").update({"is_default": False}).eq("is_default", True).execute()
                        sb.insert("depots", data)
                        st.success("✅ Almacén registrado correctamente.")
                        st.rerun()
                    else:
                        st.error("❌ No se pudo geocodificar la dirección.")
                else:
                    st.warning("⚠️ Completa todos los campos obligatorios.")

    # ---------- LISTAR ALMACENES ----------
    st.subheader("📋 Lista de Almacenes Registrados")
    depots = sb.get("depots")
    if not depots:
        st.info("No hay almacenes registrados todavía.")
        return

    df = pd.DataFrame(depots)
    st.dataframe(df[["name", "address", "is_default", "created_at"]], use_container_width=True)

    # ---------- ACTUALIZAR ESTADO ----------
    with st.expander("✏️ Actualizar almacén"):
        depot_ids = {d["name"]: d["id"] for d in depots}
        selected = st.selectbox("Seleccionar almacén", list(depot_ids.keys()))
        new_default = st.checkbox("Marcar este almacén como predeterminado")
        if st.button("Actualizar"):
            if new_default:
                sb.client.table("depots").update({"is_default": False}).eq("is_default", True).execute()
            sb.client.table("depots").update({"is_default": new_default}).eq("id", depot_ids[selected]).execute()
            st.success("🔄 Almacén actualizado.")
            st.rerun()

    # ---------- ELIMINAR ----------
    with st.expander("🗑️ Eliminar almacén"):
        depot_ids = {d["name"]: d["id"] for d in depots}
        selected_del = st.selectbox("Seleccionar almacén a eliminar", list(depot_ids.keys()))
        if st.button("Eliminar definitivamente"):
            sb.client.table("depots").delete().eq("id", depot_ids[selected_del]).execute()
            st.warning(f"🚫 Almacén '{selected_del}' eliminado.")
            st.rerun()

# ---------------- MAIN ----------------
if __name__ == "__main__":
    main()
