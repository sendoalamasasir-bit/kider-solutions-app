import streamlit as st
import pandas as pd
import warnings

# Ocultar advertencias
warnings.filterwarnings('ignore')

# Configuración de la página web
st.set_page_config(page_title="Escáner Kider Solutions", page_icon="⚙️", layout="wide")

def generar_reporte_automatico(archivo_cargado):
    try:
        # 1. Leer el Excel directamente desde el archivo que sube el usuario
        df = pd.read_excel(archivo_cargado, engine='openpyxl')
        df.columns = df.columns.astype(str).str.strip()

        # 2. DETECCIÓN INTELIGENTE DE COLUMNAS
        col_articulo = next((c for c in df.columns if 'rt' in c and 'culo' in c), 'Artículo')
        col_desc = next((c for c in df.columns if 'Descrip' in c), 'Descripción')
        col_color = next((c for c in df.columns if 'Color' in c), 'Color')
        col_kg_pieza = next((c for c in df.columns if 'Pieza' in c), 'Kg.Pin.Pieza')
        col_stock = next((c for c in df.columns if 'Stock' in c), 'Kg.Pin.Stock')
        col_calle = next((c for c in df.columns if 'Calle' in c and 'N' in c), 'NºCalle')
        col_pdte = next((c for c in df.columns if 'Pdte' in c), 'C.Pdte.Fab') 

        columnas_carga = [c for c in df.columns if 'Carga' in c]
        col_carga_final = columnas_carga[-1] if columnas_carga else 'Carga'

        # 3. Limpieza de datos general
        df[col_articulo] = df[col_articulo].astype(str).str.strip()
        df[col_color] = df[col_color].astype(str).str.strip()
        df[col_calle] = df[col_calle].astype(str).str.strip()
        df[col_carga_final] = df[col_carga_final].astype(str).str.strip()

        df[col_kg_pieza] = pd.to_numeric(df[col_kg_pieza].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df[col_stock] = pd.to_numeric(df[col_stock].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df[col_pdte] = pd.to_numeric(df[col_pdte].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # 4. FILTRAR PRIORIDADES (Terminan en 0 o 1)
        df_prioridad = df[df[col_carga_final].str.endswith('0') | df[col_carga_final].str.endswith('1')]

        if df_prioridad.empty:
            return "ℹ️ **No se han encontrado artículos con Carga 0 o 1 en este archivo.**"

        # Empezamos a construir la respuesta con formato Markdown
        respuesta = "### 🚀 REPORTE AUTOMÁTICO DE PRIORIDADES\n---\n"

        # 5. PROCESAR CADA PRIORIDAD ENCONTRADA
        for index, fila in df_prioridad.iterrows():
            articulo = fila[col_articulo]
            if articulo == 'nan' or not articulo:
                continue
            
            desc = fila[col_desc]
            color = fila[col_color]
            kg_pieza = fila[col_kg_pieza]
            stock = fila[col_stock]
            calle = fila[col_calle]
            cantidad = fila[col_pdte]
            carga_val = fila[col_carga_final]

            if cantidad == 0:
                col_lanzada = next((c for c in df.columns if 'Lanzada' in c), None)
                if col_lanzada:
                    cantidad = pd.to_numeric(str(fila[col_lanzada]).replace(',', '.'), errors='coerce')
                    if pd.isna(cantidad): cantidad = 0

            necesidad_principal = kg_pieza * cantidad
            sobrante = stock - necesidad_principal

            respuesta += f"#### 🎯 PRIORIDAD: **{articulo}** (Carga: {carga_val})\n"
            respuesta += f"> 📝 {desc}\n>\n"
            respuesta += f"> 🎨 **Color:** {color} | **Uds:** {cantidad} | **NºCalle:** {calle}\n>\n"
            respuesta += f"> 📊 **Stock actual:** {round(stock, 2)} Kg ➡️ **Necesitas:** {round(necesidad_principal, 2)} Kg\n>\n"
            
            # 6. ANÁLISIS DE LA PRIORIDAD
            if sobrante < 0:
                respuesta += f"> ❌ **ALERTA ROJA:** Faltan {abs(round(sobrante, 2))} Kg. ¡No puedes seguir!\n"
            else:
                respuesta += f"> ✅ **OK:** Sobran {round(sobrante, 2)} Kg. Calculando resto de la calle...\n"
                
                # 7. PREDICCIÓN DE LA CALLE
                if calle != 'nan' and calle != '':
                    resto_calle = df[(df[col_calle] == calle) & (df[col_color] == color) & (df.index != index)]
                    
                    if not resto_calle.empty:
                        necesidad_resto = 0
                        items_resto = 0
                        
                        for _, fila_resto in resto_calle.iterrows():
                            cant_resto = pd.to_numeric(str(fila_resto[col_pdte]).replace(',', '.'), errors='coerce')
                            if pd.isna(cant_resto): cant_resto = 0
                                
                            necesidad_resto += fila_resto[col_kg_pieza] * cant_resto
                            items_resto += cant_resto
                            
                        respuesta += f">\n> 🛣️ **PREDICCIÓN NºCalle [{calle}]:**\n"
                        respuesta += f"> * {int(items_resto)} uds esperando en esta calle con color {color}.\n"
                        respuesta += f"> * Necesitan {round(necesidad_resto, 2)} Kg extra.\n"
                        
                        if sobrante >= necesidad_resto:
                            respuesta += f"> * 🟢 **VÍA LIBRE:** Puedes pintar la calle entera.\n"
                        else:
                            faltante_calle = necesidad_resto - sobrante
                            respuesta += f"> * 🔴 **CUIDADO:** Pinta la prioridad, pero faltarán {round(faltante_calle, 2)} Kg para acabar la calle.\n"
                    else:
                        respuesta += f">\n> 🛣️ **PREDICCIÓN:** La calle [{calle}] está limpia. No hay más artículos con color {color}.\n"
            respuesta += "---\n"

        return respuesta

    except Exception as e:
        return f"❌ **Error inesperado:** {str(e)}"

# --- INTERFAZ VISUAL DE STREAMLIT ---
st.title("⚙️ Sistema de Producción - KIDER SOLUTIONS")
st.markdown("Sube el archivo Excel para escanear las cargas prioritarias (0 y 1) y predecir el estado de las calles.")

# Botón para subir archivo
archivo_subido = st.file_uploader("📂 Sube tu archivo Excel aquí (.xlsx)", type=["xlsx"])

# Si el usuario ha subido un archivo, mostramos el botón para analizar
if archivo_subido is not None:
    if st.button("🚀 Escanear Producción"):
        with st.spinner("Analizando inventario, prioridades y calles..."):
            resultado_texto = generar_reporte_automatico(archivo_subido)
            st.markdown(resultado_texto)
