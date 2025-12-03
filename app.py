import streamlit as st
import pandas as pd
import os
import json
import hashlib
from datetime import date, datetime, timedelta
import calendar

# ---------------------------------------------------------
# Config general
# ---------------------------------------------------------
st.set_page_config(
    page_title="Asesor Financiero Inteligente",
    page_icon="💰",
    layout="wide",
)

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
MOV_FILE = os.path.join(DATA_DIR, "movimientos.csv")

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------
# Utilidades de almacenamiento
# ---------------------------------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_movimientos():
    if not os.path.exists(MOV_FILE):
        return pd.DataFrame(columns=["username", "fecha", "tipo", "categoria", "etiqueta", "monto"])
    df = pd.read_csv(MOV_FILE)
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
    return df

def save_movimientos(df):
    df.to_csv(MOV_FILE, index=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# ---------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

# ---------------------------------------------------------
# Pantallas de autenticación
# ---------------------------------------------------------
def mostrar_login_register():
    st.title("Asesor Financiero Inteligente")
    st.subheader("Acceso")

    tab_login, tab_register = st.tabs(["Iniciar sesión", "Crear cuenta"])

    users = load_users()

    with tab_register:
        st.markdown("### Crear nueva cuenta")
        new_user = st.text_input("Nombre de usuario")
        new_pass = st.text_input("Contraseña", type="password")
        new_pass2 = st.text_input("Confirmar contraseña", type="password")

        if st.button("Registrarme"):
            if not new_user or not new_pass:
                st.warning("Debes ingresar usuario y contraseña.")
            elif new_user in users:
                st.error("Ese nombre de usuario ya existe.")
            elif new_pass != new_pass2:
                st.error("Las contraseñas no coinciden.")
            else:
                users[new_user] = {
                    "password_hash": hash_password(new_pass),
                    "monthly_income": 0.0,
                    "created_at": datetime.now().isoformat()
                }
                save_users(users)
                st.success("Cuenta creada correctamente. Ahora puedes iniciar sesión.")

    with tab_login:
        st.markdown("### Iniciar sesión")
        user = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")

        if st.button("Entrar"):
            if user not in users:
                st.error("Usuario no encontrado.")
            else:
                if hash_password(password) == users[user]["password_hash"]:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.success(f"Bienvenido, {user} 👋")
                    st.rerun()

                else:
                    st.error("Contraseña incorrecta.")

# ---------------------------------------------------------
# Funciones de negocio
# ---------------------------------------------------------
def obtener_resumen_usuario(username: str):
    users = load_users()
    user_info = users.get(username, {})

    ingreso_mensual = float(user_info.get("monthly_income", 0.0))
    vivienda = float(user_info.get("housing_budget", 0.0))
    mercado = float(user_info.get("market_budget", 0.0))
    transporte_diario = float(user_info.get("transport_daily", 0.0))

    DIAS_MES = 30
    transporte_mensual = transporte_diario * DIAS_MES

    df_mov = load_movimientos()
    df_user = df_mov[df_mov["username"] == username].copy()

    hoy = date.today()

    # ================== CASO 1: SIN MOVIMIENTOS ==================
    if df_user.empty:
        gastos_mes_total = vivienda + mercado + transporte_mensual
        porcentaje_gasto = (
            (gastos_mes_total / ingreso_mensual) * 100
            if ingreso_mensual > 0
            else 0.0
        )

        gasto_hoy = 0.0
        gastos_semana = 0.0

        # Dinero disponible tras gastos fijos
        disponible = max(
            0.0, ingreso_mensual - (vivienda + mercado + transporte_mensual)
        )
        ocio_sugerido = disponible * 0.4
        ahorro_sugerido = disponible * 0.6
        ahorro_estimado = ahorro_sugerido

        # Sin movimientos, el saldo según movimientos es 0
        saldo_actual = 0.0

        return (
            float(ingreso_mensual),
            float(gasto_hoy),
            float(gastos_semana),
            float(ahorro_estimado),
            float(porcentaje_gasto),
            df_user,
            float(vivienda),
            float(mercado),
            float(transporte_mensual),
            float(disponible),
            float(ocio_sugerido),
            float(ahorro_sugerido),
            float(saldo_actual),
        )

    # ================== CASO 2: CON MOVIMIENTOS ==================
    df_user["fecha"] = pd.to_datetime(df_user["fecha"])
    df_user["solo_fecha"] = df_user["fecha"].dt.date

    gastos = df_user[df_user["tipo"] == "Gasto"].copy()
    ingresos = df_user[df_user["tipo"] == "Ingreso"].copy()

    # Gasto del día
    gasto_hoy = gastos[gastos["solo_fecha"] == hoy]["monto"].sum()

    # Gasto últimos 7 días
    hace_7_dias = hoy - timedelta(days=7)
    gastos_semana = gastos[gastos["solo_fecha"] >= hace_7_dias]["monto"].sum()

    # Gasto del mes actual (por movimientos)
    mes_actual = hoy.month
    año_actual = hoy.year
    gastos_mes_mov = gastos[
        (gastos["fecha"].dt.month == mes_actual)
        & (gastos["fecha"].dt.year == año_actual)
    ]["monto"].sum()

    # Sumamos gastos fijos para el % de gasto
    gastos_mes_total = gastos_mes_mov + vivienda + mercado + transporte_mensual

    # Dinero disponible tras gastos fijos (para ocio/ahorro)
    disponible = max(0.0, ingreso_mensual - (vivienda + mercado + transporte_mensual))

    ocio_sugerido = disponible * 0.4
    ahorro_sugerido = disponible * 0.6
    ahorro_estimado = ahorro_sugerido

    porcentaje_gasto = (
        (gastos_mes_total / ingreso_mensual) * 100 if ingreso_mensual > 0 else 0.0
    )

    # Saldo tipo “banca en línea”: ingresos - gastos registrados
    total_ingresos_mov = ingresos["monto"].sum()
    total_gastos_mov = gastos["monto"].sum()
    saldo_actual = total_ingresos_mov - total_gastos_mov

    return (
        float(ingreso_mensual),
        float(gasto_hoy),
        float(gastos_semana),
        float(ahorro_estimado),
        float(porcentaje_gasto),
        df_user,
        float(vivienda),
        float(mercado),
        float(transporte_mensual),
        float(disponible),
        float(ocio_sugerido),
        float(ahorro_sugerido),
        float(saldo_actual),
    )



# ---------------------------------------------------------
# UI principal del sistema (ya logueado)
# ---------------------------------------------------------
def app_principal():
    username = st.session_state.username
    st.sidebar.markdown(f"**Usuario:** {username}")
    opcion = st.sidebar.radio(
        "Menú",
        ["Panel principal", "Registrar movimiento", "Configurar presupuesto fijo"],
    )

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    # -------- PANEL PRINCIPAL --------
    if opcion == "Panel principal":
        st.title("Panel financiero")

        (
            ingreso_mensual,
            gasto_hoy,
            gasto_semana,
            ahorro_estimado,
            porcentaje_gasto,
            df_user,
            vivienda,
            mercado,
            transporte_mensual,
            disponible,
            ocio_sugerido,
            ahorro_sugerido,
            saldo_actual,
        ) = obtener_resumen_usuario(username)

        # Métricas principales (incluye saldo actual)
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Ingreso mensual", f"${ingreso_mensual:,.2f}")
        col2.metric("Gasto hoy", f"${gasto_hoy:,.2f}")
        col3.metric("Gasto últimos 7 días", f"${gasto_semana:,.2f}")
        col4.metric("Ahorro sugerido del mes", f"${ahorro_sugerido:,.2f}")
        col5.metric("% gasto vs ingreso", f"{porcentaje_gasto:.1f}%")
        col6.metric("Saldo según movimientos", f"${saldo_actual:,.2f}")

        st.markdown("### Presupuesto fijo configurado")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vivienda (mensual)", f"${vivienda:,.2f}")
        c2.metric("Mercado (mensual)", f"${mercado:,.2f}")
        c3.metric("Transporte (mensual)", f"${transporte_mensual:,.2f}")
        c4.metric("Dinero disponible", f"${disponible:,.2f}")

        st.markdown("### Recomendación basada en tu dinero disponible")
        if disponible <= 0:
            st.error(
                "Con el ingreso y los gastos fijos configurados, no queda dinero disponible. "
                "Intenta reducir gastos fijos o aumentar tus ingresos para poder generar ahorro."
            )
        else:
            st.write(
                f"Después de cubrir vivienda, mercado y transporte, te quedan **${disponible:,.2f}** "
                f"para otros gastos. El sistema sugiere destinar aproximadamente:\n\n"
                f"- **${ocio_sugerido:,.2f}** para ocio y gastos flexibles.\n"
                f"- **${ahorro_sugerido:,.2f}** para ahorro o fondo de emergencia."
            )

        # ---------------- Recomendaciones 1,2,6,7 ----------------
        st.markdown("### Recomendaciones adicionales")

        if df_user.empty:
            st.info(
                "Aún no hay suficientes movimientos registrados para generar recomendaciones adicionales."
            )
        else:
            hoy = date.today()
            df_gastos = df_user[df_user["tipo"] == "Gasto"].copy()
            if df_gastos.empty:
                st.info(
                    "Aún no has registrado gastos. Cuando registres algunos, el sistema podrá analizar patrones."
                )
            else:
                df_gastos["fecha"] = pd.to_datetime(df_gastos["fecha"])
                df_gastos["solo_fecha"] = df_gastos["fecha"].dt.date

                mes_actual = hoy.month
                año_actual = hoy.year
                dias_mes = calendar.monthrange(año_actual, mes_actual)[1]
                dia_actual = hoy.day

                # ---- (1) Gastas demasiado rápido en el mes
                gastos_mes_actual = df_gastos[
                    (df_gastos["fecha"].dt.month == mes_actual)
                    & (df_gastos["fecha"].dt.year == año_actual)
                ]["monto"].sum()

                gastos_fijos = vivienda + mercado + transporte_mensual
                presupuesto_variable = max(0.0, ingreso_mensual - gastos_fijos)

                if presupuesto_variable > 0 and gastos_mes_actual > 0:
                    ritmo_gasto = gastos_mes_actual / presupuesto_variable
                    ritmo_tiempo = dia_actual / dias_mes  # % del mes transcurrido

                    if ritmo_gasto > ritmo_tiempo * 1.2:
                        st.warning(
                            "💡 Estás gastando más rápido de lo esperado este mes. "
                            "Si mantienes este ritmo, podrías quedarte sin dinero disponible antes de final de mes. "
                            "Intenta reducir gastos discrecionales en los próximos días."
                        )

                # ---- (2) Categoría más “peligrosa” del mes
                gastos_cat_hist = df_gastos.groupby("categoria")["monto"].sum()
                gastos_cat_mes = df_gastos[
                    (df_gastos["fecha"].dt.month == mes_actual)
                    & (df_gastos["fecha"].dt.year == año_actual)
                ].groupby("categoria")["monto"].sum()

                if not gastos_cat_mes.empty:
                    ratios = {}
                    n_meses = max(1, df_gastos["fecha"].dt.to_period("M").nunique())
                    for cat, val_mes in gastos_cat_mes.items():
                        hist_total = gastos_cat_hist.get(cat, 0.0)
                        prom_mensual_cat = (
                            hist_total / n_meses if hist_total > 0 else 0.0
                        )
                        if prom_mensual_cat > 0:
                            ratios[cat] = val_mes / prom_mensual_cat

                    if ratios:
                        cat_peligrosa = max(ratios, key=ratios.get)
                        factor = ratios[cat_peligrosa]
                        if factor > 1.2:
                            st.info(
                                f"📊 Este mes tu categoría más exigente es **{cat_peligrosa}**. "
                                f"Estás gastando aproximadamente un { (factor - 1) * 100:.1f}% más que tu promedio en esa categoría."
                            )

                # ---- (6) Recomendación diaria
                gastos_por_dia = (
                    df_gastos.groupby("solo_fecha")["monto"].sum().sort_index()
                )
                if len(gastos_por_dia) >= 3:  # al menos 3 días con datos
                    prom_diario = gastos_por_dia.mean()
                    gasto_hoy_val = gastos_por_dia.get(hoy, 0.0)

                    if prom_diario > 0 and gasto_hoy_val > prom_diario * 1.3:
                        st.warning(
                            "📅 Hoy has gastado más de lo habitual. "
                            "Considera no hacer más gastos por hoy para mantenerte dentro de tu presupuesto semanal."
                        )
                    elif prom_diario > 0 and 0 < gasto_hoy_val < prom_diario * 0.7:
                        st.success(
                            "✅ Hoy has mantenido un buen control de tus gastos. "
                            "Vas por buen camino para cumplir tus metas semanales."
                        )

                # ---- (7) Recomendación semanal
                hace_7 = hoy - timedelta(days=7)
                hace_14 = hoy - timedelta(days=14)

                gastos_semana_actual = df_gastos[
                    (df_gastos["solo_fecha"] >= hace_7)
                ]["monto"].sum()
                gastos_semana_anterior = df_gastos[
                    (df_gastos["solo_fecha"] >= hace_14)
                    & (df_gastos["solo_fecha"] < hace_7)
                ]["monto"].sum()

                if gastos_semana_anterior > 0 and gastos_semana_actual > 0:
                    cambio = (
                        (gastos_semana_actual - gastos_semana_anterior)
                        / gastos_semana_anterior
                        * 100
                    )
                    if cambio > 10:
                        st.warning(
                            f"📈 Esta semana has gastado un {cambio:.1f}% más que la semana pasada. "
                            "Revisa especialmente los gastos opcionales."
                        )
                    elif cambio < -10:
                        st.success(
                            f"📉 Esta semana has gastado un {abs(cambio):.1f}% menos que la semana pasada. "
                            "Sigue así para acercarte a tus metas de ahorro."
                        )

        # ----- Movimientos recientes -----
        st.markdown("---")
        st.subheader("Movimientos recientes")

        if df_user.empty:
            st.info("Aún no has registrado movimientos.")
        else:
            df_user = df_user.sort_values("fecha", ascending=False)
            st.dataframe(
                df_user[["fecha", "tipo", "categoria", "etiqueta", "monto"]],
                use_container_width=True,
            )

    # -------- REGISTRAR MOVIMIENTO --------
    elif opcion == "Registrar movimiento":
        st.title("Registrar movimiento")

        df_mov = load_movimientos()

        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=date.today())
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            categoria = st.selectbox(
                "Categoría",
                [
                    "Vivienda",
                    "Comida",
                    "Transporte",
                    "Servicios",
                    "Ocio",
                    "Salud",
                    "Deudas",
                    "Otros",
                ],
            )
        with col2:
            monto = st.number_input("Monto", min_value=0.0, step=10.0)
            etiqueta = st.text_input("Etiqueta / descripción")

        if st.button("Guardar movimiento"):
            if monto <= 0:
                st.warning("El monto debe ser mayor que 0.")
            else:
                nuevo = pd.DataFrame(
                    [
                        {
                            "username": username,
                            "fecha": datetime.combine(fecha, datetime.min.time()),
                            "tipo": tipo,
                            "categoria": categoria,
                            "etiqueta": etiqueta,
                            "monto": float(monto),
                        }
                    ]
                )
                df_mov = pd.concat([df_mov, nuevo], ignore_index=True)
                save_movimientos(df_mov)
                st.success("Movimiento guardado correctamente.")

    # -------- CONFIG PRESUPUESTO FIJO --------
    elif opcion == "Configurar presupuesto fijo":
        st.title("Configuración de presupuesto fijo")

        users = load_users()
        user_info = users.get(username, {"monthly_income": 0.0})

        ingreso_actual = float(user_info.get("monthly_income", 0.0))
        vivienda_actual = float(user_info.get("housing_budget", 0.0))
        mercado_actual = float(user_info.get("market_budget", 0.0))
        transporte_diario_actual = float(user_info.get("transport_daily", 0.0))

        st.markdown("### Ingresos y gastos fijos")

        col1, col2 = st.columns(2)
        with col1:
            nuevo_ingreso = st.number_input(
                "Ingreso mensual (salario + otros ingresos)",
                min_value=0.0,
                value=float(ingreso_actual),
                step=50.0,
            )
            gasto_vivienda = st.number_input(
                "Gasto mensual en vivienda",
                min_value=0.0,
                value=float(vivienda_actual),
                step=50.0,
            )
        with col2:
            gasto_mercado = st.number_input(
                "Gasto mensual en mercado / supermercado",
                min_value=0.0,
                value=float(mercado_actual),
                step=50.0,
            )
            gasto_transporte_diario = st.number_input(
                "Gasto diario en transporte (pasajes, gasolina, etc.)",
                min_value=0.0,
                value=float(transporte_diario_actual),
                step=1.0,
            )

        DIAS_MES = 30
        transporte_mensual_est = gasto_transporte_diario * DIAS_MES

        st.info(
            f"Con un gasto diario de transporte de ${gasto_transporte_diario:,.2f}, "
            f"el sistema estima un gasto mensual aproximado de ${transporte_mensual_est:,.2f} "
            f"(asumiendo {DIAS_MES} días al mes)."
        )

        if st.button("Guardar configuración"):
            users[username]["monthly_income"] = float(nuevo_ingreso)
            users[username]["housing_budget"] = float(gasto_vivienda)
            users[username]["market_budget"] = float(gasto_mercado)
            users[username]["transport_daily"] = float(gasto_transporte_diario)
            save_users(users)
            st.success("Presupuesto fijo actualizado correctamente.")




# ---------------------------------------------------------
# Punto de entrada de la app
# ---------------------------------------------------------
if not st.session_state.logged_in:
    mostrar_login_register()
else:
    app_principal()
