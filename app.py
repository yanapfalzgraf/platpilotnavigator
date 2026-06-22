import streamlit as st
import os
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
import pandas as pd
import math
import ast

DATA_SCHEMA_VERSION = "restaurant_filter_single_parquet_lazy_v1"

KITCHEN_MAP = {
    "European": "European",
    "Asian": "Asian",
    "Chinese": "Chinese",
    "Japanese": "Japanese",
    "Mexican": "Mexican",
    "Latin American": "Latin_American",
    "Middle Eastern": "Middle_Eastern",
    "African": "African",
    "Italian": "Italian",
    "Mediterranean": "Mediterranean",
    "South Asian": "South_Asian",
    "American Traditional": "American_Traditional",
    "Vegetarian / Vegan": "Vegetarian&Vegan",
    "American New": "American_New",
    "Burgers": "Burgers",
    "Fast Food": "Fast_Food",
    "Pizza": "Pizza",
    "Breakfast & Brunch": "Breakfast&Brunch",
    "Coffee & Tea": "Coffee&Tea",
    "Healthy Options": "Healthy_Options",
    "Chicken": "Chicken",
    "Seafood": "Seafood",
    "Sandwiches": "Sandwiches",
    "Noodles": "Noodles",
    "Soup": "Soup",
    "Tacos": "Tacos",
    "Hot Dogs": "Hot_Dogs",
    "Desserts": "Desserts",
    "Bakeries": "Bakeries",
    "Juice & Smoothies": "Juice&Smoothies",
    "Steak & Barbeque": "Steak&Barbeque",
    "Wraps": "Wraps",
    "Bars & Nightlife": "Bars&Nightlife",
    "Delis": "Delis",
    "Casual & Quick": "Casual&Quick",
    "Diners": "Diners"
}


# Kategorien aus One-Hot-Spalten extrahieren
category_columns = [
    "African","American_New","American_Traditional","Asian","Bakeries","Bars&Nightlife",
    "Breakfast&Brunch","Burgers","Casual&Quick","Chicken","Chinese","Coffee&Tea","Delis",
    "Desserts","Diners","European","Fast_Food","Healthy_Options","Hot_Dogs","Italian",
    "Japanese","Juice&Smoothies","Latin_American","Mediterranean","Mexican","Middle_Eastern",
    "Noodles","Pizza","Sandwiches","Seafood","Soup","South_Asian","Steak&Barbeque","Tacos",
    "Tapas","Vegetarian&Vegan","Wraps"
]

def extract_categories(row):
    return [col for col in category_columns if row.get(col, 0) == 1]


def normalize_attributes(attr):
    if isinstance(attr, dict):
        return attr
    if isinstance(attr, str):
        try:
            parsed = ast.literal_eval(attr)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}



def fix_attribute_names(attr):
    attr = normalize_attributes(attr)

    # Parquet-Spalte heißt RestaurantsGoodForGroups,
    # UI-/Anzeige-Logik nutzt GoodForGroups.
    if "RestaurantsGoodForGroups" in attr and "GoodForGroups" not in attr:
        attr["GoodForGroups"] = attr.get("RestaurantsGoodForGroups")

    # Parquet-Spalte Quiet wird für Lautstärke genutzt.
    if "Quiet" in attr and "NoiseLevel" not in attr:
        attr["NoiseLevel"] = "quiet" if truthy_attr(attr.get("Quiet")) else None

    return attr


def truthy_attr(value):
    if value is True:
        return True
    if value is False or value is None:
        return False

    if isinstance(value, (int, float)):
        return value == 1

    s = str(value).strip().lower().strip("u'\"")

    return s in {
        "1", "true", "yes", "free", "paid",
        "beer_and_wine", "full_bar"
    }

PRICE_ORDER = ["€", "€€", "€€€", "€€€€"]


def normalize_price(value):
    if value is None or pd.isna(value):
        return "€€"

    s = str(value).strip()

    if s in PRICE_ORDER:
        return s
    if s in {"1", "1.0", "$"}:
        return "€"
    if s in {"2", "2.0", "$$"}:
        return "€€"
    if s in {"3", "3.0", "$$$"}:
        return "€€€"
    if s in {"4", "4.0", "$$$$"}:
        return "€€€€"

    return "€€"


@st.cache_data(show_spinner="Restaurantdaten werden geladen ...")
def load_and_prepare_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    possible_paths = [
        os.path.join(base_dir, "Daten", "restaurant_filter.parquet"),
        os.path.join(base_dir, "restaurant_filter.parquet"),
    ]

    rest_path = next((p for p in possible_paths if os.path.exists(p)), None)

    if rest_path is None:
        st.error(
            "restaurant_filter.parquet wurde nicht gefunden. "
            "Lege die Datei entweder in den Ordner 'Daten' neben app.py "
            "oder direkt neben app.py."
        )
        st.stop()

    df = pd.read_parquet(rest_path)

    # Einheitliche Anzeigenamen, falls durch frühere Merges *_x-Spalten entstanden sind.
    if "name" not in df.columns and "name_x" in df.columns:
        df["name"] = df["name_x"]
    if "city" not in df.columns and "city_x" in df.columns:
        df["city"] = df["city_x"]
    if "state" not in df.columns and "state_x" in df.columns:
        df["state"] = df["state_x"]
    if "latitude" not in df.columns and "latitude_x" in df.columns:
        df["latitude"] = df["latitude_x"]
    if "longitude" not in df.columns and "longitude_x" in df.columns:
        df["longitude"] = df["longitude_x"]

    # Kategorien: Deine Parquet-Datei hat One-Hot-Spalten wie Japanese, Asian, Pizza usw.
    available_category_columns = [col for col in category_columns if col in df.columns]

    if available_category_columns:
        df["categories"] = df[available_category_columns].eq(1).apply(
            lambda row: row.index[row].tolist(),
            axis=1
        )
    elif "categories" in df.columns:
        df["categories"] = df["categories"].apply(
            lambda x: x if isinstance(x, list)
            else ([c.strip() for c in str(x).split(",") if c.strip()] if pd.notna(x) else [])
        )
    else:
        df["categories"] = [[] for _ in range(len(df))]

    # Preis: Deine Parquet-Datei hat PriceLevel.
    if "PriceLevel" in df.columns:
        df["price"] = df["PriceLevel"].apply(normalize_price)
    elif "price" in df.columns:
        df["price"] = df["price"].apply(normalize_price)
    else:
        df["price"] = "€€"

    # Bewertung: Deine Parquet-Datei hat stars.
    if "stars" in df.columns:
        df["rating"] = df["stars"]
    elif "rating" not in df.columns:
        df["rating"] = 0

    # Attribute: Deine Parquet-Datei hat einzelne 0/1-Spalten.
    # Daraus bauen wir wieder ein attributes-Dict, damit alle UI-Filter gleich bleiben.
    attr_columns = [
        "BusinessAcceptsCreditCards",
        "BikeParking",
        "RestaurantsTakeOut",
        "WheelchairAccessible",
        "HappyHour",
        "OutdoorSeating",
        "HasTV",
        "RestaurantsReservations",
        "DogsAllowed",
        "GoodForKids",
        "RestaurantsGoodForGroups",
        "BusinessParking",
        "Alcohol",
        "Quiet",
        "WiFi",
    ]

    available_attr_columns = [col for col in attr_columns if col in df.columns]

    if "attributes" in df.columns:
        df["attributes"] = df["attributes"].apply(normalize_attributes)
    elif available_attr_columns:
        df["attributes"] = df[available_attr_columns].apply(
            lambda row: row.to_dict(),
            axis=1
        )
    else:
        df["attributes"] = [{} for _ in range(len(df))]

    df["attributes"] = df["attributes"].apply(fix_attribute_names)

    # Distanz wird später dynamisch aus latitude/longitude und User-Standort berechnet.
    if "distance_km" not in df.columns:
        df["distance_km"] = 0.0

    if "review_count" not in df.columns:
        df["review_count"] = 0

    if "hours" in df.columns:
        df["hours"] = df["hours"].apply(normalize_attributes)
    else:
        df["hours"] = [{} for _ in range(len(df))]

    if "address" not in df.columns:
        df["address"] = ""

    restaurants_list = df.to_dict(orient="records")
    return df, restaurants_list



if (
    st.session_state.get("data_schema_version") != DATA_SCHEMA_VERSION
    or "merged" not in st.session_state
    or "restaurants_list" not in st.session_state
):
    df_merged, restaurants_list = load_and_prepare_data()
    st.session_state["merged"] = df_merged
    st.session_state["restaurants_list"] = restaurants_list
    st.session_state["data_schema_version"] = DATA_SCHEMA_VERSION
else:
    df_merged = st.session_state["merged"]


# Initialisierung
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

if "selected_extras" not in st.session_state:
    st.session_state["selected_extras"] = []

if "new_coords" not in st.session_state:
    st.session_state["new_coords"] = PHILADELPHIA_CENTER.copy()


# Hilfsfunktionen
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


@st.cache_data(ttl=3600, show_spinner=False)
def reverse_geocode_cached(lat, lon):
    return reverse_geocode(lat, lon)


def is_within_philadelphia(lat, lon):
    return (
        PHILADELPHIA_BOUNDS["min_lat"] <= lat <= PHILADELPHIA_BOUNDS["max_lat"]
        and PHILADELPHIA_BOUNDS["min_lon"] <= lon <= PHILADELPHIA_BOUNDS["max_lon"]
    )

def toggle_extra(extra: str):
    sel = st.session_state["selected_extras"]
    if extra in sel:
        sel.remove(extra)
    else:
        sel.append(extra)
# -------------------------- Filter-Logik --------------------------

def in_price_range(price_symbol: str, selected_range: tuple[str, str]) -> bool:
    if price_symbol not in PRICE_ORDER:
        return True
    lo, hi = selected_range
    return PRICE_ORDER.index(lo) <= PRICE_ORDER.index(price_symbol) <= PRICE_ORDER.index(hi)


def within_distance(dist_km: float, max_km: int) -> bool:
    return max_km == 0 or dist_km <= max_km


def haversine_distance_km(lat1, lon1, lat2, lon2):
    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
    except Exception:
        return 0.0

    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )

    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_restaurant_distance_km(r, user_coords):
    return haversine_distance_km(
        user_coords.get("lat", PHILADELPHIA_CENTER["lat"]),
        user_coords.get("lon", PHILADELPHIA_CENTER["lon"]),
        r.get("latitude", PHILADELPHIA_CENTER["lat"]),
        r.get("longitude", PHILADELPHIA_CENTER["lon"]),
    )


def passes_rating(rating: float, flag_4_plus: bool) -> bool:
    try:
        rating = float(rating)
    except Exception:
        rating = 0.0
    return (not flag_4_plus) or rating >= 4.0


def matches_kitchen(categories, selected_kitchen):
    if not selected_kitchen:
        return True

    mapped = []
    for k in selected_kitchen:
        clean = k.split(" ", 1)[1] if " " in k else k
        mapped.append(KITCHEN_MAP.get(clean, clean))

    cats = set(categories)
    return any(m in cats for m in mapped)


def build_attr_mapping(attr: dict) -> dict[str, bool]:
    attr = fix_attribute_names(attr)

    return {
        "WLAN": truthy_attr(attr.get("WiFi")),
        "Outdoor": truthy_attr(attr.get("OutdoorSeating")),
        "Kreditkarte": truthy_attr(attr.get("BusinessAcceptsCreditCards")),
        "Reservierung": truthy_attr(attr.get("RestaurantsReservations")),
        "Takeout": truthy_attr(attr.get("RestaurantsTakeOut")),
        "P Auto": truthy_attr(attr.get("BusinessParking")),
        "Happy Hour": truthy_attr(attr.get("HappyHour")),
        "Hunde": truthy_attr(attr.get("DogsAllowed")),
        "TV": truthy_attr(attr.get("HasTV")),
        "Rollstuhl": truthy_attr(attr.get("WheelchairAccessible")),
        "Alkohol": truthy_attr(attr.get("Alcohol")),
        "Kinder": truthy_attr(attr.get("GoodForKids")),
        "Gruppen": truthy_attr(attr.get("GoodForGroups")) or truthy_attr(attr.get("RestaurantsGoodForGroups")),
        "Lautstärke": truthy_attr(attr.get("NoiseLevel")) or truthy_attr(attr.get("Quiet")),
        "P Fahrrad": truthy_attr(attr.get("BikeParking")),
    }


def restaurant_has_selected_extras(r, selected_extras):
    if not selected_extras:
        return True

    attr_map = build_attr_mapping(r.get("attributes", {}))

    return all(
        attr_map.get(extra, False)
        for extra in selected_extras
    )


def filter_restaurants(all_restaurants: list[dict], filters: dict) -> list[dict]:
    sel_extras = filters.get("extras", [])
    user_coords = filters.get("coords", PHILADELPHIA_CENTER)

    debug_counts = {
        "geladen": len(all_restaurants),
        "nach_kueche": 0,
        "nach_preis": 0,
        "nach_rating": 0,
        "nach_entfernung": 0,
        "nach_extras": 0,
    }

    results = []

    for r in all_restaurants:
        r_distance = get_restaurant_distance_km(r, user_coords)

        if not matches_kitchen(r.get("categories", []), filters.get("kitchen", [])):
            continue
        debug_counts["nach_kueche"] += 1

        if not in_price_range(
            normalize_price(r.get("price", "€€")),
            filters.get("price_range", ("€", "€€€€"))
        ):
            continue
        debug_counts["nach_preis"] += 1

        if not passes_rating(r.get("rating", 0), filters.get("use_rating", False)):
            continue
        debug_counts["nach_rating"] += 1

        if not within_distance(r_distance, filters.get("distance", 0)):
            continue
        debug_counts["nach_entfernung"] += 1

        if not restaurant_has_selected_extras(r, sel_extras):
            continue
        debug_counts["nach_extras"] += 1

        r = dict(r)
        r["distance_km"] = round(r_distance, 2)
        results.append(r)

    results.sort(
        key=lambda x: (
            x.get("distance_km", 999),
            -float(x.get("rating", 0) or 0),
            -int(x.get("review_count", 0) or 0),
        )
    )

    st.session_state["filter_debug"] = debug_counts
    return results


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
    stadt, strasse = reverse_geocode_cached(lat, lon)

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
            new_stadt, new_strasse = reverse_geocode_cached(new_lat, new_lon)

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
    st.markdown("---")
    # 1. Bevorzugte Küche (mit sichtbarer Gruppierung)
   
    st.markdown("### 1. Bevorzugte Küche")

    grouped_options = {
        "🔵 CUISINE ─────────────────────────": [
            "🇪🇺 European", "🍜 Asian", "🥡 Chinese", "🍣 Japanese",
            "🌮 Mexican", "🥙 Latin American", "🧆 Middle Eastern",
            "🌍 African", "🇮🇹 Italian", "🥗 Mediterranean",
            "🇮🇳 South Asian", "🇺🇸 American Traditional",
            "🌱 Vegetarian / Vegan", "🇺🇸 American New"
        ],
        "🟢 DISH ─────────────────────────": [
            "🍔 Burgers", "🍟 Fast Food", "🍕 Pizza", "🥞 Breakfast & Brunch",
            "🧋 Coffee & Tea", "🥗 Healthy Options", "🍗 Chicken",
            "🐟 Seafood", "🥪 Sandwiches", "🍜 Noodles", "🍲 Soup",
            "🌮 Tacos", "🌭 Hot Dogs", "🍰 Desserts", "🥐 Bakeries",
            "🧃 Juice & Smoothies", "🥩 Steak & Barbeque", "🌯 Wraps"
        ],
        "🟣 VENUE ─────────────────────────": [
            "🍸 Bars & Nightlife", "☕ Coffee & Tea", "🥪 Delis",
            "🍳 Breakfast & Brunch", "🍽️ Casual & Quick", "🍽️ Diners"
        ]
    }

    def build_grouped_list(groups: dict):
        items = []
        for header, values in groups.items():
            items.append(header)   # farbiger Header
            items.extend(values)   # echte Items
        return items

    grouped_list = build_grouped_list(grouped_options)

    selected_raw = st.multiselect(
        "Wähle eine oder mehrere Kategorien:",
        grouped_list
    )

    # Header entfernen
    selected_kitchen = [
        x for x in selected_raw
        if not x.startswith(("🔵", "🟢", "🟣"))
    ]


    st.markdown("")

    st.markdown("### 2. Preisniveau")
    price_labels = ["€", "€€", "€€€", "€€€€"]
    price_range = st.select_slider("Preis auswählen:", options=price_labels, value=("€", "€€"))
    st.write(f"Ausgewählter Bereich: {price_range[0]} bis {price_range[1]}")
    st.markdown("")
    st.markdown("### 3. Bewertung")
    use_rating = st.toggle("⭐ 4 Sterne und mehr", value=False)
    st.markdown("")
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
    st.markdown("")
    # 6. Extras
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
    st.markdown("")

    if st.button("🔍 Suche starten"):
        st.session_state["filters"] = {
            "kitchen": selected_kitchen,
            "price_range": price_range,
            "use_rating": use_rating,
            "distance": distance,
            "extras": list(st.session_state["selected_extras"]),
            "coords": st.session_state["coords"].copy()
        }

        # RICHTIG: Liste aus Session State holen
        restaurants_list = st.session_state["restaurants_list"]

        filtered = filter_restaurants(
            restaurants_list, st.session_state["filters"]
        )

        st.session_state["results"] = filtered
        st.session_state["visible_results"] = 20
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

    if "visible_results" not in st.session_state:
        st.session_state["visible_results"] = 20

    visible = min(st.session_state["visible_results"], len(results))
    visible_results = results[:visible]
    f = st.session_state.get("filters", {})
    extras_txt = ", ".join(f.get("extras", [])) or "–"
    kitchen_txt = ", ".join([k for k in f.get("kitchen", [])]) or "–"
    price_txt = " bis ".join(f.get("price_range", ("€", "€€€€")))
    dist_txt = "egal" if f.get("distance", 0) == 0 else f"bis {f.get('distance')} km"
    rating_txt = "ab 4⭐" if f.get("use_rating") else "alle"

    st.markdown(
        f"**Aktive Filter:** Küche: {kitchen_txt} | Preis: {price_txt} | Bewertung: {rating_txt} | Entfernung: {dist_txt} | Extras: {extras_txt}"
    )
    st.markdown("---")
    results = st.session_state["results"] 
    if not results:
        st.error("Keine Restaurants gefunden.")
        if "filter_debug" in st.session_state:
            with st.expander("Warum keine Ergebnisse?", expanded=True):
                st.write(st.session_state["filter_debug"])
        return

    st.markdown(f"### {len(results)} Restaurants gefunden")

    for r in visible_results:
        header = (
            f"{r.get('name', 'Unbekannt')} — ⭐ {r.get('rating', 0)} | {r.get('price', '€€')} | {r.get('distance_km', 0)} km | 👁️ {r.get('review_count', 0)}"
        )

        with st.expander(header):
            st.markdown(f"**Kategorien:** {', '.join(r.get('categories', []))}")
            st.markdown(f"**Bewertung:** ⭐ {r.get('rating', 0)} ({r.get('review_count', 0)} Reviews)")

            st.subheader("Öffnungszeiten")
            hours_data = normalize_attributes(r.get("hours", {}))
            if hours_data:
                for day, hours in hours_data.items():
                    st.write(f"{day}: {hours}")
            else:
                st.write("Keine Öffnungszeiten hinterlegt")

            st.subheader("Extras (Restaurant)")
            extras_list = []
            attr = normalize_attributes(r.get("attributes", {}))

            if truthy_attr(attr.get("BusinessAcceptsCreditCards")):
                extras_list.append("Kreditkarte")
            if truthy_attr(attr.get("RestaurantsTakeOut")):
                extras_list.append("Takeout")
            if truthy_attr(attr.get("WiFi")) and str(attr.get("WiFi")).lower().strip("u'\"") != "no":
                extras_list.append("WLAN")
            if truthy_attr(attr.get("WheelchairAccessible")):
                extras_list.append("Rollstuhlgerecht")
            if truthy_attr(attr.get("HappyHour")):
                extras_list.append("Happy Hour")
            if truthy_attr(attr.get("OutdoorSeating")):
                extras_list.append("Outdoor")
            if truthy_attr(attr.get("HasTV")):
                extras_list.append("TV")
            if truthy_attr(attr.get("RestaurantsReservations")):
                extras_list.append("Reservierung")
            if truthy_attr(attr.get("DogsAllowed")):
                extras_list.append("Hunde erlaubt")
            if truthy_attr(attr.get("Alcohol")) and str(attr.get("Alcohol")).lower().strip("u'\"") not in {"no", "none"}:
                extras_list.append("Alkohol")
            if truthy_attr(attr.get("GoodForKids")):
                extras_list.append("Kinderfreundlich")
            if truthy_attr(attr.get("GoodForGroups")):
                extras_list.append("Gruppenfreundlich")
            if attr.get("NoiseLevel"):
                noise = attr["NoiseLevel"]
                noise_map = {"quiet": "Leise", "average": "Normal", "loud": "Laut", "very_loud": "Sehr laut"}
                extras_list.append(f"Lautstärke: {noise_map.get(noise, noise)}")
            if truthy_attr(attr.get("BusinessParking")) and str(attr.get("BusinessParking")).lower() not in {"none", "no", "false", "{}"}:
                extras_list.append("Parken")
            if truthy_attr(attr.get("BikeParking")):
                extras_list.append("Fahrradparkplätze")

            st.write(", ".join(extras_list) if extras_list else "Keine Extras hinterlegt")

            st.subheader("Adresse")
            st.write(r.get("address", "Keine Adresse hinterlegt"))

            maps_url = f"https://www.google.com/maps/search/?api=1&query={r.get('address') or r.get('name', '')}"

            st.link_button("📍 Route öffnen", maps_url)


    if visible < len(results):
        st.markdown("---")
        remaining = len(results) - visible
        next_batch = min(20, remaining)

        if st.button(
            f"Weitere {next_batch} Restaurants laden ({visible}/{len(results)})",
            use_container_width=True
        ):
            st.session_state["visible_results"] = min(
                visible + 20,
                len(results)
            )
            st.rerun()
    elif results:
        st.caption("Alle gefundenen Restaurants wurden angezeigt.")


# Routing
# ---------------------------------------------------------

if st.session_state.page == "form":
    show_form()
else:
    show_results()
