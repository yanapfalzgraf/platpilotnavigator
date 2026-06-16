import streamlit as st
import os
import json
from streamlit_folium import st_folium
import folium

# Session-State initialisieren
if "coords" not in st.session_state:
    st.session_state["coords"] = {"lat": 40.7128, "lon": -74.0060}  # Default: New York
if "show_map" not in st.session_state:
    st.session_state["show_map"] = False

# Sidebar ausblenden
hide_sidebar = """
    <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }
        .block-container { padding-left: 2rem; padding-right: 2rem; }
    </style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)

# JSON laden
@st.cache_data
def load_restaurants():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "restaurants.json")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

if "restaurants" not in st.session_state:
    st.session_state["restaurants"] = load_restaurants()

# UI START
st.title("🍽️ PlatePilot Navigator")
st.markdown("---")

# Aktueller Standort
lat = st.session_state["coords"]["lat"]
lon = st.session_state["coords"]["lon"]

# Begrüßung + Standort in einer Zeile
colA, colB = st.columns([3, 2])

with colA:
    st.markdown(f"### Hi Mike 👋")

with colB:
    if st.button(f"📍 {lat:.5f}, {lon:.5f}  ✏️"):
        st.session_state["show_map"] = True

# Wenn Karte geöffnet werden soll
if st.session_state["show_map"]:

    st.markdown("### 📍 Standort bearbeiten")

    lat = st.session_state["coords"]["lat"]
    lon = st.session_state["coords"]["lon"]

    # Karte erstellen
    m = folium.Map(location=[lat, lon], zoom_start=13)
    folium.Marker([lat, lon], tooltip="Aktueller Standort").add_to(m)

    # Karte anzeigen
    map_data = st_folium(m, height=400, width=700)

    # Wenn Nutzer klickt → neue Koordinaten speichern
    if map_data and map_data.get("last_clicked"):
        st.session_state["new_coords"] = {
            "lat": map_data["last_clicked"]["lat"],
            "lon": map_data["last_clicked"]["lng"]
        }

    # Neue Koordinaten anzeigen (falls vorhanden)
    if "new_coords" in st.session_state:
        st.write(
            f"Neue Koordinaten: {st.session_state['new_coords']['lat']:.6f}, "
            f"{st.session_state['new_coords']['lon']:.6f}"
        )

        # Speichern-Button
        if st.button("💾 Standort speichern"):
            st.session_state["coords"] = st.session_state["new_coords"]
            del st.session_state["new_coords"]
            st.session_state["show_map"] = False
            st.success("Standort erfolgreich aktualisiert!")
            st.rerun()
st.markdown("---")

# --- Restlicher UI-Code ---
st.markdown("#### Was willst du heute essen?")
st.button("🔄 Letzte Eingaben laden", key="load_last_inputs")

# Küche
st.markdown("### 1. Bevorzugte Küche")
kitchen_icons = ["🍔 Burger", "🍜 Asiatisch", "🍕 Pizza", "🐟 Fisch", "🥗 Salat", "🍲 Suppe"]
selected_kitchen = st.multiselect("Wähle eine oder mehrere Küchen:", kitchen_icons)
free_text = st.text_area("...oder gib Deine eigene Kriterien ein:", placeholder="z.B. vegan, spicy, glutenfrei...")

# Preis
st.markdown("### 2. Preisniveau")

# Mapping
price_labels = {
    1: "€",
    2: "€€",
    3: "€€€",
    4: "€€€€"
}

# Range-Slider
price_range = st.slider(
    "Preisniveau auswählen:",
    min_value=1,
    max_value=4,
    value=(1, 3),
    step=1,
    #format_func=lambda x: price_labels[x]
)

# Anzeige der gewählten Labels
st.write(
    f"Ausgewählter Bereich: {price_labels[price_range[0]]} bis {price_labels[price_range[1]]}"
)

# Speichern in Filter
st.session_state["price_range"] = price_range

# Bewertung
st.markdown("### 3. Bewertung")
use_rating = st.toggle("⭐ 4 Sterne und mehr", value=False)

# Entfernung
st.subheader("4. Entfernung")
distance = st.segmented_control("Entfernung (Radius)", ["≤ 1 km", "1–3 km", "≥ 10 km", "egal"], default="1–3 km")

# Extras
st.markdown("### 5. Extras")
extras = st.multiselect("Zusätzliche Kriterien:", ["WLAN", "Outdoor", "Kreditkarte", "Reservierung", "Takeout", "Parken"])

# Suche starten
if st.button("🔍 Suche starten"):

    st.session_state["filters"] = {
        "kitchen": selected_kitchen,
        "free_text": free_text,
        "price_range": price_range,
        "use_rating": use_rating,
        "distance": distance,
        "extras": extras
    }

    filtered = st.session_state["restaurants"]
    st.session_state["results"] = filtered

    st.success(f"{len(filtered)} Restaurants gefunden!")

    st.switch_page("pages/2_Results.py")
