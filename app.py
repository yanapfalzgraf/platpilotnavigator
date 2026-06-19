import streamlit as st
import os
import json
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="platepilot", timeout=10)


def reverse_geocode(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), language="de")
    except Exception:
        return None, None

    if location and "address" in location.raw:
        addr = location.raw["address"]
        stadt = addr.get("city") or addr.get("town") or addr.get("village")
        strasse = addr.get("road")
        return stadt, strasse

    return None, None



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

# Adresse holen
stadt, strasse = reverse_geocode(lat, lon)

# 3 Spalten: Name | Adresse | Button
colA, colB, colC = st.columns([7, 2.5, 2.5])

with colA:
    st.markdown("### Hi Mike 👋")

with colB:
    st.markdown(
        f"""
        <div style='font-size:15px; line-height:1.2; margin-top:6px;'>
            📍{(stadt or "Unbekannte Stadt")}, {(strasse or "Unbekannte Straße")}
        </div>
        """,
        unsafe_allow_html=True
    )

with colC:
    #if st.button(f"{lat:.5f}, {lon:.5f} ✏️"):
    if st.button(f"Bearbeiten ✏️"):
        st.session_state["show_map"] = True


# Wenn Karte geöffnet werden soll
if st.session_state["show_map"]:

    st.markdown("### 📍 Standort bearbeiten")

    # Karte mit aktuellem Standort
    m = folium.Map(location=[39.9526, -75.1652], zoom_start=13)

    folium.Marker([lat, lon], tooltip="Aktueller Standort").add_to(m)

    map_data = st_folium(m, height=400, width=700)

    # Klick auf Karte → neue Koordinaten speichern
    if map_data and map_data.get("last_clicked"):
        st.session_state["new_coords"] = {
            "lat": map_data["last_clicked"]["lat"],
            "lon": map_data["last_clicked"]["lng"]
        }

    # Neue Koordinaten anzeigen (falls vorhanden)
    if "new_coords" in st.session_state:
        new_lat = st.session_state["new_coords"]["lat"]
        new_lon = st.session_state["new_coords"]["lon"]

        # Reverse Geocoding für neue Koordinaten
        stadt, strasse = reverse_geocode(new_lat, new_lon)

        st.markdown(
            f"""
            <div style='font-size:16px; line-height:1.2;'>
                {stadt or "Stadt "},
                 {strasse or "Straße"}<br><br>
            </div>
            """,
            unsafe_allow_html=True
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
st.markdown("")
# Küche
st.markdown("### 1. Bevorzugte Küche")
kitchen_icons = ["🍔 Burger", "🍜 Asiatisch", "🍕 Pizza", "🐟 Fisch", "🥗 Salat", "🍲 Suppe"]
selected_kitchen = st.multiselect("Wähle eine oder mehrere Küchen:", kitchen_icons)
#free_text = st.text_area("...oder gib Deine eigene Kriterien ein:", placeholder="z.B. vegan, spicy, glutenfrei...")
st.markdown("")
# Preis
st.markdown("### 2. Preisniveau")

# Mapping
# Preislabels
price_labels = ["€", "€€", "€€€", "€€€€"]

# Slider mit Euro-Symbolen
price_range = st.select_slider(
    "Preis auswählen:",
    options=price_labels,
    value=("€", "€€")
)

# Anzeige
st.write(f"Ausgewählter Bereich: {price_range[0]} bis {price_range[1]}")


# Speichern in Filter
st.session_state["price_range"] = price_range
st.markdown("")
# Bewertung
st.markdown("### 3. Bewertung")
use_rating = st.toggle("⭐ 4 Sterne und mehr", value=False)
st.markdown("")
# Entfernung
st.subheader("4. Entfernung")
#distance = st.segmented_control("Entfernung (Radius)", ["≤ 1 km", "1–3 km", "≥ 10 km", "egal"], default="1–3 km")

# Defaults
if "distance_slider" not in st.session_state:
    st.session_state.distance_slider = 0  # 0 = egal


# Checkbox "egal"
egal = st.checkbox("egal", value=True, key="dist_egal")

# Logik: abh. von "egal" Slider-Status setzen
if egal:
    # egal aktiv → Slider deaktiviert und auf 0
    st.session_state.distance_slider = 0
    slider_disabled = True
else:
    # egal aus → Slider aktiv
    slider_disabled = False
    # falls noch 0, sinnvollen Startwert setzen
    if st.session_state.distance_slider == 0:
        st.session_state.distance_slider = 1

# Slider
distance = st.slider(
    "Entfernung auswählen:",
    min_value=0,
    max_value=10,
    value=st.session_state.distance_slider,
    step=1,
    disabled=slider_disabled,
    key="dist_slider"
)

# State aktualisieren
st.session_state.distance_slider = distance

# Anzeige
if egal:
    st.write("Ausgewählt: egal")
else:
    if distance == 10:
        st.write("Ausgewählt: 10+ km")
    else:
        st.write(f"Ausgewählt: bis {distance} km")

st.markdown("")
# Extras
st.markdown("### 5. Extras")
extras = st.multiselect("Zusätzliche Kriterien:", ["WLAN", "Outdoor", "Kreditkarte", "Reservierung", "Takeout", "Parken"])

# Suche starten
if st.button("🔍 Suche starten"):

    st.session_state["filters"] = {
        "kitchen": selected_kitchen,
        "price_range": price_range,
        "use_rating": use_rating,
        "distance": distance,
        "extras": extras
    }

    filtered = st.session_state["restaurants"]
    st.session_state["results"] = filtered

    st.success(f"{len(filtered)} Restaurants gefunden!")

    st.switch_page("pages/2_Results.py")
