"""
config.py
=========
Constantes globales: paleta de colores, URLs externas y textos de etiquetas.
"""

COLORES = {
    "verde":   "#648A96",  # azul grisáceo principal
    "naranja": "#E8B8B8",  # rosa bebé
    "rojo":    "#C0392B",  # alertas críticas
    "gris":    "#888888",
    "crema":   "#F6F0E6",
    "oscuro":  "#1A2E35",
}

# GeoJSON de CCAA españolas (fuente: AEMET / IGN simplificado)
CCAA_GEOJSON_URL = (
    "https://raw.githubusercontent.com/codeforgermany/click_that_hood/"
    "main/public/data/spain-communities.geojson"
)