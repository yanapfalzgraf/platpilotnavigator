import streamlit as st
import os
import json
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim


# Initialisiereung
# ---------------------------------------------------------

PHILADELPHIA_CENTER = {"lat": 39.9526, "lon": -75.1652}
PHILADELPHIA_BOUNDS = {
    "min_lat": 39.80,
    "max_lat": 40.10,
    "min_lon": -75.35,
    "max_lon": -74.95,
}

geolocator = Nominatim(user_agent="platepilot", timeout=10)

if "page" not in st.session_state:
    st.session_state.page = "form"

if "coords" not in st.session_state:
    st.session_state["coords"] = PHILADELPHIA_CENTER.copy()

if "show_map" not in st.session_state:
    st.session_state["show_map"] = False

# WICHTIG: Liste statt Set, damit Klickreihenfolge erhalten bleibt
if "selected_extras" not in st.session_state:
    st.session_state["selected_extras"] = []

if "selected_location" not in st.session_state:
    st.session_state["selected_location"] = []

if "new_coords" not in st.session_state:
    st.session_state["new_coords"] = PHILADELPHIA_CENTER.copy()


# Hilffunktionen
# ---------------------------------------------------------

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


def is_within_philadelphia(lat, lon):
    return (
        PHILADELPHIA_BOUNDS["min_lat"] <= lat <= PHILADELPHIA_BOUNDS["max_lat"]
        and PHILADELPHIA_BOUNDS["min_lon"] <= lon <= PHILADELPHIA_BOUNDS["max_lon"]
    )


@st.cache_data
def load_restaurants():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "restaurants.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


if "restaurants" not in st.session_state:
    st.session_state["restaurants"] = load_restaurants()


# Toggle behält Reihenfolge: neu -> append; vorhanden -> remove

def toggle_extra(extra: str):
    sel = st.session_state["selected_extras"]
    if extra in sel:
        sel.remove(extra)
    else:
        sel.append(extra)


# -------------------------- Filter-Logik --------------------------

PRICE_ORDER = ["€", "€€", "€€€", "€€€€"]


def in_price_range(price_symbol: str, selected_range: tuple[str, str]) -> bool:
    if price_symbol not in PRICE_ORDER:
        return True
    lo, hi = selected_range
    return PRICE_ORDER.index(lo) <= PRICE_ORDER.index(price_symbol) <= PRICE_ORDER.index(hi)


def within_distance(dist_km: float, max_km: int) -> bool:
    return max_km == 0 or dist_km <= max_km


def passes_rating(rating: float, flag_4_plus: bool) -> bool:
    return (not flag_4_plus) or rating >= 4.0


def matches_kitchen(categories: list[str], selected_kitchen: list[str]) -> bool:
    if not selected_kitchen:
        return True
    wanted = {k.split(" ", 1)[1] if " " in k else k for k in selected_kitchen}
    cats = set(categories)
    for w in wanted:
        for c in cats:
            if w.lower() in c.lower():
                return True
    return False


def matches_location(categories: list[str], selected_location: list[str]) -> bool:
    if not selected_location:
        return True
    cats = set(categories)
    for wanted in selected_location:
        for c in cats:
            if wanted.lower() in c.lower():
                return True
    return False


def build_attr_mapping(attr: dict) -> dict[str, bool]:
    return {
        "WLAN": bool(attr.get("WiFi") and attr.get("WiFi") != "no"),
        "Outdoor": bool(attr.get("OutdoorSeating")),
        "Kreditkarte": bool(attr.get("BusinessAcceptsCreditCards")),
        "Reservierung": bool(attr.get("RestaurantsReservations")),
        "Takeout": bool(attr.get("RestaurantsTakeOut")),
        "P Auto": bool(attr.get("BusinessParking") and attr.get("BusinessParking") != "none"),
        "Happy Hour": bool(attr.get("HappyHour")),
        "Hunde": bool(attr.get("DogsAllowed")),
        "TV": bool(attr.get("HasTV")),
        "Rollstuhl": bool(attr.get("WheelchairAccessible")),
        "Alkohol": bool(attr.get("Alcohol") and attr.get("Alcohol") != "none"),
        "Kinder": bool(attr.get("GoodForKids")),
        "Gruppen": bool(attr.get("GoodForGroups")),
        "Lautstärke": attr.get("NoiseLevel") is not None,
        "P Fahrrad": bool(attr.get("BikeParking")),
    }


def restaurant_has_selected_extras(r: dict, selected_extras: list[str]) -> bool:
    if not selected_extras:
        return True
    m = build_attr_mapping(r.get("attributes", {}))
    return all(m.get(e, False) for e in selected_extras)


def filter_restaurants(all_restaurants: list[dict], filters: dict) -> list[dict]:
    sel_extras = filters.get("extras", [])
    sel_location = filters.get("location", [])

    return [
        r for r in all_restaurants
        if matches_kitchen(r.get("categories", []), filters.get("kitchen", []))
        and matches_location(r.get("categories", []), sel_location)
        and in_price_range(r.get("price", "€€"), filters.get("price_range", ("€", "€€€€")))
        and passes_rating(r.get("rating", 0), filters.get("use_rating", False))
        and within_distance(r.get("distance_km", 0), filters.get("distance", 0))
        and restaurant_has_selected_extras(r, sel_extras)
    ]


# Formular für den User
# ---------------------------------------------------------

def show_form():

    hide_sidebar = """
        <style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="stSidebarNav"] { display: none; }
            .block-container { padding-left: 2rem; padding-right: 2rem; }
        </style>
    """
    st.markdown(hide_sidebar, unsafe_allow_html=True)

    st.title("🍽️ PlatePilot Navigator")
    st.markdown("---")

    lat = st.session_state["coords"]["lat"]
    lon = st.session_state["coords"]["lon"]
    stadt, strasse = reverse_geocode(lat, lon)

    if stadt is None or "philadelphia" not in (stadt or "").lower():
        stadt = "Philadelphia"

    colA, colB, colC = st.columns([7, 2.5, 2.5])

    with colA:
        st.markdown("### Hi Mike 👋")

    with colB:
        st.markdown(
            f"""
            <div style='font-size:15px; line-height:1.2; margin-top:6px;'>
                📍{(stadt or "Philadelphia")}, {(strasse or "Unbekannte Straße")}
            </div>
            """,
            unsafe_allow_html=True
        )

    with colC:
        if st.button("Bearbeiten ✏️"):
            st.session_state["show_map"] = True

    if st.session_state["show_map"]:
        st.markdown("### 📍 Standort bearbeiten")
        st.caption("Der auswählbare Bereich ist auf Philadelphia begrenzt.")

        m = folium.Map(location=[PHILADELPHIA_CENTER["lat"], PHILADELPHIA_CENTER["lon"]], zoom_start=12)

        folium.Rectangle(
            bounds=[
                [PHILADELPHIA_BOUNDS["min_lat"], PHILADELPHIA_BOUNDS["min_lon"]],
                [PHILADELPHIA_BOUNDS["max_lat"], PHILADELPHIA_BOUNDS["max_lon"]],
            ],
            color="blue",
            fill=True,
            fill_opacity=0.08,
            tooltip="Philadelphia Bereich"
        ).add_to(m)

        folium.Marker([lat, lon], tooltip="Aktueller Standort").add_to(m)

        map_data = st_folium(m, height=400, width=700)

        if map_data and map_data.get("last_clicked"):
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lon = map_data["last_clicked"]["lng"]

            if is_within_philadelphia(clicked_lat, clicked_lon):
                st.session_state["new_coords"] = {
                    "lat": clicked_lat,
                    "lon": clicked_lon
                }
            else:
                st.warning("Bitte wähle einen Standort innerhalb von Philadelphia.")

        if "new_coords" in st.session_state:
            new_lat = st.session_state["new_coords"]["lat"]
            new_lon = st.session_state["new_coords"]["lon"]
            new_stadt, new_strasse = reverse_geocode(new_lat, new_lon)

            if new_stadt is None or "philadelphia" not in (new_stadt or "").lower():
                new_stadt = "Philadelphia"

            st.markdown(
                f"""
                <div style='font-size:16px; line-height:1.2;'>
                    {new_stadt or "Philadelphia"}, {new_strasse or "Unbekannte Straße"}<br><br>
                </div>
                """,
                unsafe_allow_html=True
            )

        if st.button("💾 Standort speichern"):
            new_lat = st.session_state["new_coords"]["lat"]
            new_lon = st.session_state["new_coords"]["lon"]

            if is_within_philadelphia(new_lat, new_lon):
                st.session_state["coords"] = st.session_state["new_coords"]
                st.session_state["show_map"] = False
                st.success("Standort in Philadelphia erfolgreich aktualisiert!")
                st.rerun()
            else:
                st.error("Standort kann nur innerhalb von Philadelphia gespeichert werden.")

    st.markdown("---")

    st.markdown("#### Was willst du heute essen?")
    st.button("🔄 Letzte Eingaben laden", key="load_last_inputs")

    st.markdown("### 1. Bevorzugte Küche")
    kitchen_icons = [
        "🍔 Burgers", "🍟 Fast Food", "🍕 Pizza", "🥞 Breakfast & Brunch", "🧋 Coffee & Tea",
        "🥗 Healthy Options", "🥦 Vegetarian / Vegan", "🍣 Japanese & Sushi", "🍜 Asian", "🥡 Chinese",
        "🌮 Mexican", "🐟 Seafood", "🍗 Chicken", "🇺🇸 American", "🇪🇺 European",
        "🥩 Steak & Barbeque", "🍰 Desserts", "🧃 Juice & Smoothies", "🥙 Latin American",
        "🧆 Middle Eastern", "🌍 African", "🍸 Bars & Nightlife",
    ]

    selected_kitchen = st.multiselect("Wähle eine oder mehrere Küchen:", kitchen_icons)

    st.markdown("### 2. Preisniveau")
    price_labels = ["€", "€€", "€€€", "€€€€"]
    price_range = st.select_slider("Preis auswählen:", options=price_labels, value=("€", "€€"))
    st.write(f"Ausgewählter Bereich: {price_range[0]} bis {price_range[1]}")

    st.markdown("### 3. Bewertung")
    use_rating = st.toggle("⭐ 4 Sterne und mehr", value=False)

    st.subheader("4. Entfernung")

    if "distance_slider" not in st.session_state:
        st.session_state.distance_slider = 0

    egal = st.checkbox("egal", value=True, key="dist_egal")

    if egal:
        st.session_state.distance_slider = 0
        slider_disabled = True
    else:
        slider_disabled = False
        if st.session_state.distance_slider == 0:
            st.session_state.distance_slider = 1

    distance = st.slider(
        "Entfernung auswählen:", min_value=0, max_value=10, value=st.session_state.distance_slider,
        step=1, disabled=slider_disabled, key="dist_slider"
    )

    st.session_state.distance_slider = distance

    if egal:
        st.write("Ausgewählt: egal")
    else:
        st.write(f"Ausgewählt: bis {distance} km")

    st.markdown("### 5. Location")

    location_options = [
        "Sushi Bar",
        "Café",
        "Bäckerei",
        "Fast Food",
        "Pizzeria",
        "Bar",
        "Dessert Shop"
    ]

    selected_location = st.multiselect(
        "Wähle eine oder mehrere Locations:",
        location_options,
        default=st.session_state["selected_location"],
        key="location_multiselect"
    )

    st.session_state["selected_location"] = selected_location

    # 6. Extras-Chips
    # ---------------------------------------------------------
    st.markdown("### 6. Extras")

    extras_list = [
        "WLAN", "Outdoor", "Kreditkarte", "Reservierung", "Takeout",
        "P Auto", "Happy Hour", "Hunde", "TV", "Rollstuhl",
        "Alkohol", "Kinder", "Gruppen", "Lautstärke", "P Fahrrad"
    ]

    cols_per_row = 5
    rows = [extras_list[i:i + cols_per_row] for i in range(0, len(extras_list), cols_per_row)]

    for row in rows:
        cols = st.columns(len(row))
        for col, extra in zip(cols, row):
            with col:
                is_selected = extra in st.session_state["selected_extras"]
                button_type = "primary" if is_selected else "secondary"
                if st.button(
                    f"{'✓ ' if is_selected else ''}{extra}", key=f"chip_{extra}",
                    type=button_type, use_container_width=True
                ):
                    toggle_extra(extra)
                    st.rerun()

    sel = st.session_state["selected_extras"]
    if sel:
        st.write(f"**Deine Extras-Filter:** {', '.join(sel)}")

    if st.button("🔍 Suche starten"):
        st.session_state["filters"] = {
            "kitchen": selected_kitchen,
            "price_range": price_range,
            "use_rating": use_rating,
            "distance": distance,
            "location": selected_location,
            "extras": list(st.session_state["selected_extras"])
        }

        filtered = filter_restaurants(
            st.session_state["restaurants"], st.session_state["filters"]
        )

        st.session_state["results"] = filtered
        st.session_state.page = "results"
        st.rerun()



# Restaurant-Ergebnisse
# ---------------------------------------------------------

def show_results():

    if st.button("⬅️ Zurück zur Suche"):
        st.session_state.page = "form"
        st.rerun()

    st.title("🍽️ Deine Restaurant-Ergebnisse")
    st.markdown("---")

    if "results" not in st.session_state:
        st.warning("Bitte zuerst eine Suche durchführen.")
        return

    results = st.session_state["results"]

    f = st.session_state.get("filters", {})
    extras_txt = ", ".join(f.get("extras", [])) or "–"
    kitchen_txt = ", ".join([k for k in f.get("kitchen", [])]) or "–"
    location_txt = ", ".join(f.get("location", [])) or "–"
    price_txt = " bis ".join(f.get("price_range", ("€", "€€€€")))
    dist_txt = "egal" if f.get("distance", 0) == 0 else f"bis {f.get('distance')} km"
    rating_txt = "ab 4⭐" if f.get("use_rating") else "alle"

    st.markdown(
        f"**Aktive Filter:** Küche: {kitchen_txt} | Location: {location_txt} | Preis: {price_txt} | Bewertung: {rating_txt} | Entfernung: {dist_txt} | Extras: {extras_txt}"
    )
    st.markdown("---")

    if not results:
        st.error("Keine Restaurants gefunden.")
        return

    st.markdown(f"### {len(results)} Restaurants gefunden")

    for r in results:
        header = (
            f"{r['name']} — ⭐ {r['rating']} | {r['price']} | {r['distance_km']} km | 👁️ {r['review_count']}"
        )

        with st.expander(header):
            st.markdown(f"**Kategorien:** {', '.join(r['categories'])}")
            st.markdown(f"**Bewertung:** ⭐ {r['rating']} ({r['review_count']} Reviews)")

            st.subheader("Öffnungszeiten")
            for day, hours in r["hours"].items():
                st.write(f"{day}: {hours}")

            st.subheader("Extras (Restaurant)")
            extras_list = []
            attr = r.get("attributes", {})

            if attr.get("BusinessAcceptsCreditCards"):
                extras_list.append("Kreditkarte")
            if attr.get("RestaurantsTakeOut"):
                extras_list.append("Takeout")
            if attr.get("WiFi") and attr["WiFi"] != "no":
                extras_list.append("WLAN")
            if attr.get("WheelchairAccessible"):
                extras_list.append("Rollstuhlgerecht")
            if attr.get("HappyHour"):
                extras_list.append("Happy Hour")
            if attr.get("OutdoorSeating"):
                extras_list.append("Outdoor")
            if attr.get("HasTV"):
                extras_list.append("TV")
            if attr.get("RestaurantsReservations"):
                extras_list.append("Reservierung")
            if attr.get("DogsAllowed"):
                extras_list.append("Hunde erlaubt")
            if attr.get("Alcohol") and attr["Alcohol"] != "none":
                extras_list.append("Alkohol")
            if attr.get("GoodForKids"):
                extras_list.append("Kinderfreundlich")
            if attr.get("GoodForGroups"):
                extras_list.append("Gruppenfreundlich")
            if attr.get("NoiseLevel"):
                noise = attr["NoiseLevel"]
                noise_map = {"quiet": "Leise", "average": "Normal", "loud": "Laut", "very_loud": "Sehr laut"}
                extras_list.append(f"Lautstärke: {noise_map.get(noise, noise)}")
            if attr.get("BusinessParking") and attr["BusinessParking"] != "none":
                extras_list.append("Parken")
            if attr.get("BikeParking"):
                extras_list.append("Fahrradparkplätze")

            st.write(", ".join(extras_list) if extras_list else "Keine Extras hinterlegt")

            st.subheader("Adresse")
            st.write(r["address"])

            maps_url = f"[Google Maps](https://www.google.com/maps/search/?api=1&query={r['address']})"

            st.link_button("📍 Route öffnen", maps_url)


# Routing
# ---------------------------------------------------------

if st.session_state.page == "form":
    show_form()
else:
    show_results()

