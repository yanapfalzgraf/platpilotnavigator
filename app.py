import streamlit as st
import os
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
import pandas as pd
import math
import ast
#KITCHEN_MAP verbindet die sichtbaren UI-Namen wie "Latin American" mit den Spaltennamen in der Datei, zum Beispiel "Latin_American".

DATA_SCHEMA_VERSION = "score_search_v1"

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


EXTRA_MAP = {
    "Wi-Fi": "Wi-Fi",
    "Outdoor": "Outdoor Seating",
    "Credit Card": "Credit Card",
    "Reservations": "Reservations",
    "Takeout": "Takeout",
    "Parking": "Parking",
    "Happy Hour": "Happy Hour",
    "Dogs Allowed": "Dogs Allowed",
    "TV": "TV",
    "Wheelchair": "Wheelchair Accessible",
    "Alcohol": "Alcohol",
    "Quiet": "Noise Level",
    "Bike Parking": "Bike Parking",
    "Good for Kids": "Good for Kids",
    "Good for Groups": "Good for Groups",
}
def normalize_extra_name(extra: str) -> str:
    return EXTRA_MAP.get(extra, extra)

# Kategorien aus One-Hot-Spalten extrahieren
category_columns = [ #category_columns enthält alle möglichen Restaurant-Kategorien aus der Parquet-Datei.
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


def truthy_attr(value): #hilfsfunktion, die prüft, ob ein Attribut als "wahr" (Ture) interpretiert werden soll
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

#legt die Preisreihenfolge fest
PRICE_ORDER = ["﹩", "﹩﹩", "﹩﹩﹩", "﹩﹩﹩﹩"]

#normalize_price() wandelt verschiedene Preisformate in $, $$, $$$, $$$$ um.
def normalize_price(value):#wandelt verschiedene Preisformate um:
    if value is None or pd.isna(value):
        return "﹩﹩"

    s = str(value).strip()

    if s in PRICE_ORDER:
        return s
    if s in {"1", "1.0", "﹩"}:
        return "﹩"
    if s in {"2", "2.0", "﹩﹩"}:
        return "﹩﹩"
    if s in {"3", "3.0", "﹩﹩﹩"}:
        return "﹩﹩﹩"
    if s in {"4", "4.0", "﹩﹩﹩﹩"}:
        return "﹩﹩﹩﹩"

    return "﹩﹩"

#Daten vorbereiten
@st.cache_data(show_spinner="Loading restaurant data...") #Die Restaurantdaten werden nicht bei jedem Klick neu geladen. Streamlit merkt sich das geladene DataFrame. Das macht die App schneller.
def load_and_prepare_data(): #sucht die Datei:restaurant_filter.parquet
    base_dir = os.path.dirname(os.path.abspath(__file__))

    possible_paths = [
        os.path.join(base_dir, "score_search.parquet"),
        os.path.join(base_dir, "Daten", "score_search.parquet")
    ]

    rest_path = next((p for p in possible_paths if os.path.exists(p)), None)

    if rest_path is None:
        st.error(
            "restaurant_filter.parquet was not found. "
            "Please place the file either in the 'Data' folder next to app.py "
            "or in the same directory as app.py."
        )
        st.stop()

    df = pd.read_parquet(rest_path)

    # Dann prüft die Datei, ob wichtige Spalten existieren, zum Beispiel:Dann prüft sie, ob wichtige Spalten existieren, zum Beispiel:name, city, latitude, longitude, stars, PriceLevel, attributes
    #Falls Spalten anders heißen, etwa name_x, werden sie vereinheitlicht.
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

    # Preis: Parquet-Datei hat PriceLevel.
    if "PriceLevel" in df.columns:
        df["price"] = df["PriceLevel"].apply(normalize_price)
    elif "price" in df.columns:
        df["price"] = df["price"].apply(normalize_price)
    else:
        df["price"] = "﹩﹩"

    # Bewertung: Parquet-Datei hat stars.
    if "stars" in df.columns:
        df["rating"] = df["stars"]
    elif "rating" not in df.columns:
        df["rating"] = 0

    # Attribute: Parquet-Datei hat einzelne 0/1-Spalten.
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



if (#speichert App-Zustände, zum Beispiel:aktuelle Seite, aktueller Standort, ausgewählte Extras,Suchergebnisse.
    st.session_state.get("data_schema_version") != DATA_SCHEMA_VERSION
    or "merged" not in st.session_state #speichert aktuellen Nutzerzustand:Welche Seite? Welche Filter? Welche Extras? Welche Ergebnisse?
    or "restaurants_list" not in st.session_state
):
    df_merged, restaurants_list = load_and_prepare_data() #wird nur einmal richtig geladen, danach aus dem Cache genommen.
    st.session_state["merged"] = df_merged
    st.session_state["restaurants_list"] = restaurants_list #wird es zusätzlich in session_state gespeichert...So kann die App später schnell darauf zugreifen.
    # Wenn man die Parquet-Datei ändert, aber Streamlit alte Daten zeigt, liegt es oft am Cache.
    st.session_state["data_schema_version"] = DATA_SCHEMA_VERSION
else:
    df_merged = st.session_state["merged"]


# Initialisierung
# ---------------------------------------------------------
#Der Standardstandort ist Philadelphia:

PHILADELPHIA_CENTER = {"lat": 39.9526, "lon": -75.1652}
PHILADELPHIA_BOUNDS = {
    "min_lat": 39.80,
    "max_lat": 40.10,
    "min_lon": -75.35,
    "max_lon": -74.95,
}

geolocator = Nominatim(user_agent="platepilot", timeout=10)

DEFAULT_FILTER_VALUES = {
    "selected_raw": [],
    "selected_kitchen": [],
    "selected_price": ("﹩", "﹩﹩"),
    "use_rating": False,
    "distance": 10,
    "selected_extras": [],
}

def reset_filter_state():
    # Setzt sowohl deine gespeicherten Filter als auch die Streamlit-Widget-Keys zurück.
    # Wichtig: Diese Funktion wird als on_click-Callback ausgeführt, bevor Streamlit
    # die Widgets neu zeichnet. Dadurch werden Preis, Rating und Distance sauber resettet.
    st.session_state["filter_values"] = DEFAULT_FILTER_VALUES.copy()
    st.session_state["selected_extras"] = []

    st.session_state["selected_categories_widget"] = []
    st.session_state["price_range_widget"] = ("﹩", "﹩﹩")
    st.session_state["rating_widget"] = False
    st.session_state["dist_slider"] = 10
    #st.session_state["dist_slider_any"] = 0
    #st.session_state["distance_slider"] = 0

    # Optional: alte Ergebnisse bleiben nicht mehr als aktive Suche sichtbar.
    st.session_state.pop("results", None)
    st.session_state.pop("filters", None)
    st.session_state["visible_results"] = 20

#Session State: merkt sich Werte pro Nutzer-Session.
#Streamlit führt bei jedem Klick die ganze Datei neu aus. Ohne session_state würde die App alles vergessen. Merkt "results", "selected_extras"

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

if "filter_values" not in st.session_state:
    st.session_state["filter_values"] = DEFAULT_FILTER_VALUES.copy()

# Widget-Keys einmalig initialisieren. Danach sind die Widgets selbst die Quelle der Wahrheit.
if "selected_categories_widget" not in st.session_state:
    st.session_state["selected_categories_widget"] = st.session_state["filter_values"].get("selected_raw", [])

if "price_range_widget" not in st.session_state:
    st.session_state["price_range_widget"] = st.session_state["filter_values"].get("selected_price", ("﹩", "﹩﹩"))

if "rating_widget" not in st.session_state:
    st.session_state["rating_widget"] = st.session_state["filter_values"].get("use_rating", False)

if "dist_slider" not in st.session_state:
    st.session_state["dist_slider"] = st.session_state["filter_values"].get("distance", 10)

# Beim App-Start Extras aus den gespeicherten Filtern wiederherstellen.
if not st.session_state["selected_extras"] and st.session_state["filter_values"].get("selected_extras"):
    st.session_state["selected_extras"] = list(st.session_state["filter_values"].get("selected_extras", []))


# Hilfsfunktionen
# ---------------------------------------------------------
#Mit reverse_geocode() wird aus Koordinaten eine Adresse gemacht.
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


@st.cache_data(ttl=3600, show_spinner=False) #speichert das Ergebnis einer Funktion, damit sie nicht jedes Mal neu berechnet wird.
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
# prüft Preisbereich.
def in_price_range(price_symbol: str, selected_range: tuple[str, str]) -> bool:
    if price_symbol not in PRICE_ORDER:
        return True
    lo, hi = selected_range
    return PRICE_ORDER.index(lo) <= PRICE_ORDER.index(price_symbol) <= PRICE_ORDER.index(hi)

def price_match_score(price_symbol: str, selected_range: tuple[str, str]) -> float:
    price_symbol = normalize_price(price_symbol)
    lo, hi = selected_range

    if price_symbol not in PRICE_ORDER:
        return 0.5

    p = PRICE_ORDER.index(price_symbol)
    lo_i = PRICE_ORDER.index(lo)
    hi_i = PRICE_ORDER.index(hi)

    if lo_i <= p <= hi_i:
        return 1.0

    distance = min(abs(p - lo_i), abs(p - hi_i))
    return max(0.0, 1.0 - 0.5 * distance)

def within_distance(dist_km: float, max_km: int) -> bool: #prüft 4-Sterne-Filter.
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


def matches_kitchen(categories, selected_kitchen): #prüft ausgewählte Küche.
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
        "Wi-Fi": truthy_attr(attr.get("WiFi")),
        "Outdoor Seating": truthy_attr(attr.get("OutdoorSeating")),
        "Credit Card": truthy_attr(attr.get("BusinessAcceptsCreditCards")),
        "Reservations": truthy_attr(attr.get("RestaurantsReservations")),
        "Takeout": truthy_attr(attr.get("RestaurantsTakeOut")),
        "Parking": truthy_attr(attr.get("BusinessParking")),
        "Happy Hour": truthy_attr(attr.get("HappyHour")),
        "Dogs Allowed": truthy_attr(attr.get("DogsAllowed")),
        "TV": truthy_attr(attr.get("HasTV")),
        "Wheelchair Accessible": truthy_attr(attr.get("WheelchairAccessible")),
        "Alcohol": truthy_attr(attr.get("Alcohol")),
        "Good for Kids": truthy_attr(attr.get("GoodForKids")),
        "Good for Groups": truthy_attr(attr.get("GoodForGroups")) or truthy_attr(attr.get("RestaurantsGoodForGroups")),
        "Noise Level": truthy_attr(attr.get("NoiseLevel")) or truthy_attr(attr.get("Quiet")),
        "Bike Parking": truthy_attr(attr.get("BikeParking")),
    }


def restaurant_has_selected_extras(r, selected_extras): #prüft Extras.
    if not selected_extras:
        return True

    attr_map = build_attr_mapping(r.get("attributes", {}))

    return all(
        attr_map.get(normalize_extra_name(extra), False)
        for extra in selected_extras
    )


def filter_restaurants(all_restaurants: list[dict], filters: dict) -> list[dict]:#kombiniert alles: Jedes Restaurant wird geprüft. Nur passende Restaurants kommen in die Ergebnisliste.
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

        #if not matches_kitchen(
        #    r.get("categories", []),
         #   filters.get("kitchen", [])
        #):
        #    continue
        debug_counts["nach_kueche"] += 1

        price_score = price_match_score(
            normalize_price(r.get("price", "﹩﹩")),
            filters.get("price_range", ("﹩", "﹩﹩﹩﹩"))
        )

        # Wird der Slider weit nach rechts geschoben,
        # wird Preis automatisch zum harten Filter.
        if filters.get("w_price", 2.0) >= 8.0 and price_score < 1.0:
            continue

        debug_counts["nach_preis"] += 1

        if not passes_rating(
            r.get("rating", 0),
            filters.get("use_rating", False)
        ):
            continue
        debug_counts["nach_rating"] += 1

        if not within_distance(
            r_distance,
            filters.get("distance", 0)
        ):
            continue
        debug_counts["nach_entfernung"] += 1

        # Extras NICHT mehr hart filtern
        # if not restaurant_has_selected_extras(...):
        #     continue

        r = dict(r)
        r["distance_km"] = round(r_distance, 2)
        results.append(r)

        # ==========================================
        # Recommendation Scoring
        # ==========================================

    alpha = filters.get("alpha", 0.6)
    w_cat = filters.get("w_cat", 4.0)
    w_attr = filters.get("w_attr", 3.0)
    w_price = filters.get("w_price", 2.0)
    #w_price = filters.get("w_price", 2.0)
    w_dist = filters.get("w_dist", 1.0)

    selected_kitchen = filters.get("kitchen", [])
    selected_extras = filters.get("extras", [])
    selected_price_range = filters.get("price_range", ("﹩", "﹩﹩﹩﹩"))
    max_distance = filters.get("distance", 0)

    for r in results:

        category_score = 1.0 if matches_kitchen(
            r.get("categories", []),
            selected_kitchen
        ) else 0.0

        if selected_extras:
            attr_map = build_attr_mapping(r.get("attributes", {}))
            matched_extras = sum(
                1 for extra in selected_extras
                if attr_map.get(normalize_extra_name(extra), False)
            )
            attribute_score = matched_extras / len(selected_extras)
        else:
            attribute_score = 1.0

        #price_score = 1.0 if in_price_range(
         #   normalize_price(r.get("price", "﹩﹩")),
        #    selected_price_range
        #) else 0.0

        if max_distance == 0:
            distance_score = 1.0
        else:
            distance_score = max(
                0.0,
                1.0 - (r.get("distance_km", 999) / max_distance)
            )

        rating_score = float(r.get("rating", 0) or 0) / 5.0
        review_score = min(
            int(r.get("review_count", 0) or 0) / 500.0,
            1.0
        )

        popularity_score = (
            0.7 * rating_score +
            0.3 * review_score
        )

        price_score = price_match_score(
            normalize_price(r.get("price", "﹩﹩")),
            selected_price_range
        )

        personalized_score = (
            w_cat * category_score +
            w_attr * attribute_score +
            w_price * price_score +
            w_dist * distance_score
        )
           

        final_score = (
            (1 - alpha) * personalized_score +
            alpha * popularity_score
        )
        r["category_score"] = round(category_score, 3)
        r["attribute_score"] = round(attribute_score, 3)
        r["price_score"] = round(price_score, 3)
        r["distance_score"] = round(distance_score, 3)
        r["popularity_score"] = round(popularity_score, 3)
        r["final_score"] = round(final_score, 3)

        #r["final_score"] = final_score

    results.sort(
        key=lambda x: x.get("final_score", 0),
        reverse=True
    )

    return results


# Formular für den User
# ---------------------------------------------------------

def show_form(): #baut Startseite

    hide_sidebar = """
        <style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="stSidebarNav"] { display: none; }
            .block-container { padding-left: 2rem; padding-right: 2rem; }
        </style>
    """
    st.markdown(hide_sidebar, unsafe_allow_html=True)

    col_logo, col_title = st.columns([0.8, 6])

    with col_logo:
        st.markdown("<div style='margin-bottom:-2px'></div>", unsafe_allow_html=True)
        st.image("platepilot.png", width=70)

    with col_title:
        st.markdown(
            """
            <div style="
                height:100px;
                display:flex;
                align-items:center;
            ">
                <h1 style="
                    margin:0;
                    padding-right:0rem;
                ">
                    PlatePilot Navigator
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    lat = st.session_state["coords"]["lat"]
    lon = st.session_state["coords"]["lon"]
    stadt, strasse = reverse_geocode_cached(lat, lon)

    if stadt is None or "philadelphia" not in (stadt or "").lower():
        stadt = "Philadelphia"

    colA, colB, colC = st.columns([8, 2.5, 2.5])

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
        if st.button("Edit  ✏️"):
            st.session_state["show_map"] = True

    if st.session_state["show_map"]:
        st.markdown("### 📍 Edit Location")
        st.caption("The selectable area is limited to Philadelphia.")

        m = folium.Map(location=[PHILADELPHIA_CENTER["lat"], PHILADELPHIA_CENTER["lon"]], zoom_start=12)

        folium.Rectangle(
            bounds=[
                [PHILADELPHIA_BOUNDS["min_lat"], PHILADELPHIA_BOUNDS["min_lon"]],
                [PHILADELPHIA_BOUNDS["max_lat"], PHILADELPHIA_BOUNDS["max_lon"]],
            ],
            color="blue",
            fill=True,
            fill_opacity=0.08,
            tooltip="Philadelphia Area"
        ).add_to(m)

        folium.Marker([lat, lon], tooltip="Current Location").add_to(m)

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
                st.warning("Please select a location within Philadelphia.")

        if "new_coords" in st.session_state:
            new_lat = st.session_state["new_coords"]["lat"]
            new_lon = st.session_state["new_coords"]["lon"]
            new_stadt, new_strasse = reverse_geocode_cached(new_lat, new_lon)

            if new_stadt is None or "philadelphia" not in (new_stadt or "").lower():
                new_stadt = "Philadelphia"

            st.markdown(
                f"""
                <div style='font-size:16px; line-height:1.2;'>
                    {new_stadt or "Philadelphia"}, {new_strasse or "Unknown Street"}<br><br>
                </div>
                """,
                unsafe_allow_html=True
            )

        if st.button("💾 Save location"):
            new_lat = st.session_state["new_coords"]["lat"]
            new_lon = st.session_state["new_coords"]["lon"]

            if is_within_philadelphia(new_lat, new_lon):
                st.session_state["coords"] = st.session_state["new_coords"]
                st.session_state["show_map"] = False
                st.success("Location successfully updated!")
                st.rerun()
            else:
                st.error("Please select a location within Philadelphia.")

    st.markdown("---")

    st.markdown("#### What would you like to eat today?")
    st.button("🔄 Reset", key="reset", on_click=reset_filter_state)
    #st.markdown("---")
    # 1. Bevorzugte Küche (mit sichtbarer Gruppierung)

    st.markdown("### 1. Cuisine / Food")

    grouped_options = {
        "🔵 CUISINE ─────────────────────────": [
            "🥨 European", "🍜 Asian", "🥡 Chinese", "🍣 Japanese",
            "🌮 Mexican", "🥙 Latin American", "🧆 Middle Eastern",
            "🌍 African", "🍝 Italian", "🥗 Mediterranean",
            "🕌 South Asian", "🍗 American Traditional",
            "🌱 Vegetarian / Vegan", "🍖 American New"
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
        "Select one or more categories:",
        grouped_list,
        key="selected_categories_widget"
    )

    # Header entfernen
    selected_kitchen = [
        x for x in selected_raw
        if not x.startswith(("🔵", "🟢", "🟣"))
    ]


    st.markdown("")
    st.markdown("### 2. Price Range")

    price_options = ["﹩", "﹩﹩", "﹩﹩﹩", "﹩﹩﹩﹩"]

    # Wichtig: select_slider muss mit einem Tuple starten, damit es ein Range-Slider bleibt.
    # Falls Streamlit vorher nur einen einzelnen String gespeichert hat, reparieren wir den Wert.

    #price_options = ["﹩", "﹩﹩", "﹩﹩﹩", "﹩﹩﹩﹩"]

    selected_price = st.select_slider(
        "Select preferred price range:",
        options=["﹩", "﹩﹩", "﹩﹩﹩", "﹩﹩﹩﹩"],
        value=("﹩", "﹩﹩"),
        key="price_range_widget"
    )

    st.write(
        f"Selected price range: {selected_price[0]} to {selected_price[1]}"
    )
    st.markdown("")

    st.markdown("### 3. Rating")

    use_rating = st.toggle(
        "⭐ 4 stars and up",
        key="rating_widget"
    )

    st.markdown("")


    st.markdown("### 4. Distance")

    distance = st.slider(
        "Select maximum distance:",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
        key="dist_slider"
    )

    st.write(f"Selected distance: up to {distance} km")

    st.markdown("")
    # 6. Extras
    # ---------------------------------------------------------
    st.markdown("### 5. Additional Options")

    extras_list = [
        "Wi-Fi", "Outdoor", "Credit Card", "Reservations", "Takeout",
        "Parking", "Happy Hour", "Dogs Allowed", "TV", "Wheelchair",
        "Alcohol",  "Quiet", "Bike Parking","Good for Kids", "Good for Groups"
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
                    st.session_state["filter_values"] = {
                        "selected_raw": selected_raw,
                        "selected_kitchen": selected_kitchen,
                        "selected_price": selected_price,
                        "use_rating": use_rating,
                        "distance": distance,
                        "selected_extras": list(st.session_state["selected_extras"]),
                    }
                    st.rerun()

    sel = st.session_state["selected_extras"]
    if sel:
        st.write(f"**Your preferences:** {', '.join(sel)}")
    #st.markdown("---")

    #st.markdown("### 6. Recommendation Settings")

    #alpha = st.slider("Personalisierung vs. Beliebtheit", 0.0, 1.0, 0.6)
    #w_cat = st.slider("Wichtigkeit Kategorie", 0.0, 10.0, 4.0)
    #w_attr = st.slider("Wichtigkeit Attribute", 0.0, 10.0, 3.0)
    #w_price = st.slider("Wichtigkeit Preis", 0.0, 10.0, 2.0)
    #w_dist = st.slider("Wichtigkeit Distanz", 0.0, 10.0, 1.0)
    st.markdown("")
      
    with st.expander("⚙️ Advanced recommendation settings", expanded=False):

        st.markdown(
                """
                <div style="display:flex; justify-content:space-between; margin-bottom:-30px;">
                    <span>🎯 Personalization</span>
                    <span>🔥 Popularity</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        alpha = st.slider(
                "",
                0.0,
                1.0,
                0.6
            )

        st.markdown(
        """
        <div style="display:flex; justify-content:space-between; margin-bottom:-25px;">
            <span>🍽️ Cuisine Flexible</span>
            <span>👨‍🍳 Strong Cuisine Match</span>
        </div>
        """,
        unsafe_allow_html=True
     )

        w_cat = st.slider(
            "",
            0.0, 10.0, 4.0
        )

        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; margin-bottom:-25px;">
                <span> 🎁 Extras Optional</span>
                <span> ✅ Must-Have Extras</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        w_attr = st.slider(
            "",
            0.0, 10.0, 3.0
        )

        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; margin-bottom:-25px;">
                <span>💰 Price Flexible</span>
                <span>🎯 Strict Price Match</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        w_price = st.slider(
            "",
            0.0, 10.0, 2.0
        )

        #price_strict = st.toggle(
        #"Only show restaurants inside selected price range",
        #value=False
        #)

        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; margin-bottom:-35px;">
                <span>🚗 Distance Flexible</span>
                <span>📍Nearby Restaurants</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        w_dist = st.slider(
            "",
            0.0, 10.0, 1.0
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔍 Find restaurants", type="primary", use_container_width=False):
        st.session_state["filter_values"] = {
            "selected_raw": selected_raw,
            "selected_kitchen": selected_kitchen,
            "selected_price": selected_price,
            "use_rating": use_rating,
            "distance": distance,
            "selected_extras": list(st.session_state["selected_extras"]),
            "alpha": alpha,
            "w_cat": w_cat,
            "w_attr": w_attr,
            "w_price": w_price,
           # "price_strict": price_strict,
            "w_dist": w_dist,
        }

        st.session_state["filters"] = {
            "kitchen": selected_kitchen,
            "price_range": selected_price,
            "use_rating": use_rating,
            "distance": distance,
            "extras": list(st.session_state["selected_extras"]),
            "coords": st.session_state["coords"].copy(),
            "alpha": alpha,
            "w_cat": w_cat,
            "w_attr": w_attr,
            "w_price": w_price,
           # "price_strict": price_strict,
            "w_dist": w_dist,
        }

        restaurants_list = st.session_state["restaurants_list"]

        filtered = filter_restaurants(
            restaurants_list,
            st.session_state["filters"]
        )

        st.session_state["results"] = filtered
        st.session_state["visible_results"] = 20
        st.session_state.page = "results"
        st.rerun()



# Restaurant-Ergebnisse
# ---------------------------------------------------------

def show_results():

    if st.button("⬅️ Back to search"):
        st.session_state.page = "form"
        st.rerun()
    st.markdown("")
    col_logo, col_title = st.columns([0.8, 6])

    with col_logo:
        st.image("platepilot.png", width=70)

    with col_title:
        st.markdown(
            """
            <h1 style="padding-top:10px;">
                Restaurant Results
            </h1>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    if "results" not in st.session_state:
        st.warning("Start a search to see results.")
        return

    results = st.session_state["results"]

    if "visible_results" not in st.session_state:
        st.session_state["visible_results"] = 20

    visible = min(st.session_state["visible_results"], len(results))
    visible_results = results[:visible]
    f = st.session_state.get("filters", {})
    extras_txt = ", ".join(f.get("extras", [])) or "–"
    kitchen_txt = ", ".join([k for k in f.get("kitchen", [])]) or "–"
    price_txt = " to ".join(f.get("price_range", ("$", "$$$$")))
    dist_txt = "any" if f.get("distance", 0) == 0 else f"up to {f.get('distance')} km"
    rating_txt = "4 stars and up" if f.get("use_rating") else "all"

    st.markdown(
        f"**Active Filters:** Cuisine: {kitchen_txt} | Price: {price_txt} | Rating: {rating_txt} | Distance: {dist_txt} | Extras: {extras_txt}"
    )
    st.markdown("---")
    results = st.session_state["results"] 
    if not results:
        st.warning(
            "Unfortunately, no restaurants match your current filters. "
            "Try adjusting your filters or increasing the search radius."
        )
        return

    st.markdown(f"### {len(results)} Restaurants Found")

    for r in visible_results:
        header = (
            f"{r.get('name', 'Unknown')} "
            f"— Score {r.get('final_score', 0):.2f} "
            f"| ⭐ {r.get('rating', 0)} "
            f"| {r.get('price', '$$')} "
            f"| {r.get('distance_km', 0)} km"
        )

        with st.expander(header):
            st.subheader("**Categories**")
            st.write(", ".join(r.get("categories", [])))
            st.markdown(f"**Rating:** ⭐ {r.get('rating', 0)} ({r.get('review_count', 0)} reviews)")

            st.subheader("Opening Hours")
            hours_data = normalize_attributes(r.get("hours", {}))

            if hours_data:

                day_map = {
                    "Monday": "Mon",
                    "Tuesday": "Tue",
                    "Wednesday": "Wed",
                    "Thursday": "Thu",
                    "Friday": "Fri",
                    "Saturday": "Sat",
                    "Sunday": "Sun"
                }

                day_order = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday"
                ]

                opening_hours = []

                for day in day_order:

                    if day not in hours_data:
                        continue

                    hours = hours_data[day]

                    if (
                        not hours
                        or hours == "None"
                        or hours == "0:0-0:0"
                        or hours == "0:00-0:00"
                    ):
                        continue

                    short_day = day_map.get(day, day)

                    opening_hours.append(
                        f"{short_day}: {hours}"
                    )

                if opening_hours:
                    st.write(" | ".join(opening_hours))
                else:
                    st.write("No opening hours available.")

            else:
                st.write("No opening hours available.")

            st.subheader("Restaurant Preferences")
            extras_list = []
            attr = normalize_attributes(r.get("attributes", {}))

            if truthy_attr(attr.get("BusinessAcceptsCreditCards")):
                extras_list.append("Credit Card")
            if truthy_attr(attr.get("RestaurantsTakeOut")):
                extras_list.append("Takeout")
            if truthy_attr(attr.get("WiFi")) and str(attr.get("WiFi")).lower().strip("u'\"") != "no":
                extras_list.append("Wi-Fi")
            if truthy_attr(attr.get("WheelchairAccessible")):
                extras_list.append("Wheelchair")
            if truthy_attr(attr.get("HappyHour")):
                extras_list.append("Happy Hour")
            if truthy_attr(attr.get("OutdoorSeating")):
                extras_list.append("Outdoor")
            if truthy_attr(attr.get("HasTV")):
                extras_list.append("TV")
            if truthy_attr(attr.get("RestaurantsReservations")):
                extras_list.append("Reservations")
            if truthy_attr(attr.get("DogsAllowed")):
                extras_list.append("Dogs Allowed")
            if truthy_attr(attr.get("Alcohol")) and str(attr.get("Alcohol")).lower().strip("u'\"") not in {"no", "none"}:
                extras_list.append("Alcohol")
            if truthy_attr(attr.get("GoodForKids")):
                extras_list.append("Good for Kids")
            if truthy_attr(attr.get("GoodForGroups")):
                extras_list.append("Good for Groups")
            if attr.get("NoiseLevel"):
                noise = attr["NoiseLevel"]
                noise_map = {"quiet": "Quiet", "average": "Average", "loud": "Loud", "very_loud": "Very loud"}
                extras_list.append(f"Noise level: {noise_map.get(noise, noise)}")
            if truthy_attr(attr.get("BusinessParking")) and str(attr.get("BusinessParking")).lower() not in {"none", "no", "false", "{}"}:
                extras_list.append("Parking")
            if truthy_attr(attr.get("BikeParking")):
                extras_list.append("Bike Parking")

           # st.write(", ".join(extras_list) if extras_list else "No extras available.")

            selected_extras = st.session_state.get("filters", {}).get("extras", [])

            matched = [
                e for e in selected_extras
                if normalize_extra_name(e) in [normalize_extra_name(x) for x in extras_list]
            ]

            other = [
                e for e in extras_list
                if e not in matched
]


            #st.subheader("Restaurant Preferences")

            if matched:
                st.markdown("**Matched Preferences**")
                st.write(", ".join(f"✓ {x}" for x in matched))

            if other:
                st.markdown("**Additional Features**")
                st.write(", ".join(other))

            if not matched and not other:
                st.write("No extras available.")

            # NUR ZUM TESTEN
            #st.markdown("---")
            #st.markdown("**Debug Scores**")

            #st.write(f"Category Score: {r.get('category_score')}")
            #st.write(f"Attribute Score: {r.get('attribute_score')}")
            #st.write(f"Price Score: {r.get('price_score')}")
            #st.write(f"Distance Score: {r.get('distance_score')}")
            #st.write(f"Popularity Score: {r.get('popularity_score')}")
            #st.write(f"Final Score: {r.get('final_score')}")

            st.markdown("")
            maps_url = f"https://www.google.com/maps/search/?api=1&query={r.get('address') or r.get('name', '')}"

            st.link_button("📍 Open route", maps_url)


    if visible < len(results):
        st.markdown("")
        remaining = len(results) - visible
        next_batch = min(20, remaining)

        if st.button(
            f"Load {next_batch} more restaurants ({visible}/{len(results)})",
            use_container_width=True
        ):
            st.session_state["visible_results"] = min(
                visible + 20,
                len(results)
            )
            st.rerun()
    elif results:
        st.caption("You've reached the end of the results.")


# Routing: Welche Seite soll gerade angezeigt werden?
# ---------------------------------------------------------

if st.session_state.page == "form":
    show_form()
else:
    show_results()

#SESSION-VERHALTEN
#App startet / Button wird geklickt
#       ↓
#Streamlit führt app.py komplett neu aus
#       ↓
#Prüfung: Sind Daten schon in session_state?
#       ↓
#Nein → load_and_prepare_data()
#       ↓
#@st.cache_data prüft:
#  Sind die Daten schon im Cache?
#       ↓
#   Nein → Parquet-Datei laden und vorbereiten
#   Ja  → gespeichertes Ergebnis verwenden
#       ↓
#DataFrame + Restaurantliste werden in session_state gespeichert
#       ↓
#App zeigt entweder:
#   page = "form"    → Suchformular
#   page = "results" → Ergebnisseite

#STRUKTUR VON DEM APP.py

#│
#├── 1. Imports
#    └── Streamlit, Pandas, Folium, Geopy, Math

#├── 2. Konstanten
#    ├── KITCHEN_MAP
#    ├── category_columns
#    └── PRICE_ORDER

#── 3. Hilfsfunktionen für Daten
#│   ├── normalize_attributes()
#│   ├── fix_attribute_names()
#│   ├── truthy_attr()
#│   └── normalize_price()
#│
#├── 4. Daten laden
#│   └── load_and_prepare_data()
#│       ├── Parquet-Datei suchen
#│       ├── Daten laden
#│       ├── Spalten vereinheitlichen
#│       ├── Kategorien bauen
#│       ├── Preise normalisieren
#│       └── Restaurantliste erstellen
#│
#├── 5. Session State initialisieren
#│   ├── page
#│   ├── coords
#│   ├── selected_extras
#│   ├── results
#│   └── restaurants_list
#│
#├── 6. Standort-Funktionen
#│   ├── reverse_geocode()
#│   ├── reverse_geocode_cached()
#│   └── is_within_philadelphia()
#│
#├── 7. Filterlogik
#│   ├── in_price_range()
#│   ├── within_distance()
#│   ├── haversine_distance_km()
#│   ├── passes_rating()
#│   ├── matches_kitchen()
#│   ├── build_attr_mapping()
#│   └── filter_restaurants()
#│
#├── 8. Suchseite
#│   └── show_form()
#│       ├── Logo + Titel
#│       ├── Standort anzeigen / bearbeiten
#│       ├── Cuisine-Filter
#│       ├── Price-Filter
#│       ├── Rating-Filter
#│       ├── Distance-Filter
#│       ├── Extra-Filter
#│       └── Find restaurants Button
#│
#├── 9. Ergebnisseite
#│   └── show_results()
#│       ├── Back Button
#│       ├── aktive Filter anzeigen
#│       ├── Restaurants anzeigen
#│       ├── Details pro Restaurant
#│       └── Load more Button
#│
#└── 10. Routing
#    ├── page == "form"    → show_form()
#    └── page == "results" → show_results()