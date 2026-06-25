import streamlit as st
import os
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
import pandas as pd
import math
import ast
import numpy as np 
from recommendation import get_recommendations
from urllib.parse import quote_plus

#score_search.parquet ist die Datenquelle. app.py lädt und bereitet diese Daten auf und sammelt die Nutzereingaben. recommendation.py 
#verwendet anschließend genau diese Daten und Eingaben, um die Scores zu berechnen und die Restaurants zu ranken. Ohne score_search.parquet 
#gäbe es keine Restaurantinformationen, auf denen der Empfehlungsalgorithmus arbeiten könnte.

#KITCHEN_MAP verbindet die sichtbaren UI-Namen wie "Latin American" mit den Spaltennamen in der Datei, zum Beispiel "Latin_American".

DATA_SCHEMA_VERSION = "score_search_v2"

#Übersetzungstabellen zwischen UI und score_search.parquet
#Streamlit speichert Daten im Cache.
#Wenn ihr später eure Parquet-Datei ändert (z.B. neue Spalten hinzufügt),
#könnte Streamlit trotzdem noch alte Daten benutzen.
#Das ist das wichtigste Dictionary für die Küchen.
#Der Benutzer sieht schöne Namen.
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
    "Desserts": "Desserts",
    "Bakeries": "Bakeries",
    "Juice & Smoothies": "Juice&Smoothies",
    "Steak & Barbeque": "Steak&Barbeque",
    "Bars & Nightlife": "Bars&Nightlife",
    "Casual & Quick": "Casual&Quick"
   
}

#Übersetzung von DB zu User Sprache
EXTRA_MAP = {
    "Wi-Fi": "WiFi",
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


#Suche nach extra im Dictionary. Wenn es vorhanden ist, gib den übersetzten Namen zurück. Wenn nicht, gib einfach den ursprünglichen Namen zurück.
def normalize_extra_name(extra: str) -> str:
    return EXTRA_MAP.get(extra, extra)

#Liste enthält alle Küchen- und Restaurantkategorien, die in der Datei score_search.parquet als One-Hot-Spalten gespeichert sind.
#1 = Restaurant gehört zu dieser Kategorie.
#0 = Restaurant gehört nicht zu dieser Kategorie.
#beim laden der daten: load_and_prepare_data -> welche der erwarten Kategorien existieren tatsächlich in der Parquet-Datei?
category_columns = [
    "European",
    "Middle_Eastern",
    "Asian",
    "Latin_American",
    "Chinese",
    "Mediterranean",
    "Japanese",
    "South_Asian",
    "Italian",
    "African",
    "American_Traditional",
    "Vegetarian&Vegan",
    "Mexican",
    "American_New",
    "Desserts",
    "Fast_Food",
    "Noodles",
    "Bakeries",
    "Juice&Smoothies",
    "Sandwiches",
    "Steak&Barbeque",
    "Chicken",
    "Healthy_Options",
    "Burgers",
    "Pizza",
    "Seafood",
    "Soup",
    "Bars&Nightlife",
    "Casual&Quick",
    "Coffee&Tea",
    "Breakfast&Brunch",
]

#alle Extras bzw. Eigenschaften eines Restaurants.
#Beim Laden der Daten: Für jedes Restaurant wird ein Attribut-Vektor erstellt.
#Liste legen die Reihenfolge der Vektoren fest.
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


#Datenvorbereitung: die Daten werden aus score_search.parquet in ein einheitliches Format gebracht werden, 
#bevor sie später von recommendation.py verwendet.
#Diese Funktion erzeugt eine leicht lesbare Kategorienliste.
def extract_categories(row): #schaut sich die Restaurant-Zeile an und sammelt alle Kategorien, die den Wert 1 besitzen
    return [col for col in category_columns if row.get(col, 0) == 1]#Hier wird aus der aktuellen Zeile ein Wert gelesen.

#In einer Parquet-Datei können Attribute unterschiedlich gespeichert sein.
#Die Funktion sorgt dafür, dass am Ende immer ein Dictionary herauskommt.
def normalize_attributes(attr): #Attribute müssen immer als dict vorliegen
    if isinstance(attr, dict):
        return attr
    if isinstance(attr, str):
        try:
            parsed = ast.literal_eval(attr)
            return parsed if isinstance(parsed, dict) else {} #Jetzt wird geprüft, ob wirklich ein Dictionary entstanden ist.
        except Exception:
            return {}
    return {} #falls attr weder dict noch str ist-> leeres Dictionary


#vereinheitlicht unterschiedliche Bezeichnungen der Restaurantattribute.
#Attribute, deren Namen in der Parquet-Datei von den in der Benutzeroberfläche
#verwendeten Namen abweichen, werden auf eine einheitliche Bezeichnung abgebildet
#Dadurch können alle nachfolgenden Programmteile unabhängig von der ursprünglichen Datenstruktur auf dieselben Attributnamen zugreifen.
def fix_attribute_names(attr):
    attr = normalize_attributes(attr)

    if "RestaurantsGoodForGroups" in attr and "GoodForGroups" not in attr:
        attr["GoodForGroups"] = attr.get("RestaurantsGoodForGroups")

    # Parquet-Spalte Quiet wird für Lautstärke genutzt.
    if "Quiet" in attr and "NoiseLevel" not in attr:
        attr["NoiseLevel"] = "quiet" if truthy_attr(attr.get("Quiet")) else None

    return attr

#sorgt dafür, dass all diese unterschiedlichen Darstellungen einheitlich als True erkannt werden.
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

#Die Logik ist weich:
#Ein gleich teures Restaurant bekommt den besten Preis-Score.
#Ein etwas günstigeres Restaurant wird kaum bestraft.
#Ein teureres Restaurant wird stärker bestraft.

#Preisreihenfolge festlegen
PRICE_ORDER = ["﹩", "﹩﹩", "﹩﹩﹩", "﹩﹩﹩﹩"]

#normalize_price() wandelt verschiedene Preisformate in $, $$, $$$, $$$$ um.
def normalize_price(value):
    if value is None or pd.isna(value):
        return "﹩﹩"


    s = str(value).strip() #Wert in einen String umwandeln

    #Zahlen in Preisstufen umwandeln
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

def format_opening_hours(hours: str) -> str:
    try:
        start, end = str(hours).split("-")
        sh, sm = start.split(":")
        eh, em = end.split(":")
        return f"{int(sh):02d}:{int(sm):02d}-{int(eh):02d}:{int(em):02d}"
    except Exception:
        return str(hours)
        
#---CASHING / ORDNER / PFAD---#
#Die Restaurantdaten werden nicht bei jedem Klick neu geladen.
#Streamlit merkt sich das geladene DataFrame. Das macht die App schneller. 
@st.cache_data(show_spinner="Loading restaurant data...") 

#Die Datei score_search.parquet finden.
#Die Daten laden und vorbereiten.
def load_and_prepare_data(): #sucht die Datei:restaurant_filter.parquet
    base_dir = os.path.dirname(os.path.abspath(__file__)) #ordner, speicherort bestimmt

#mögliche Speicherorte festlegen
    possible_paths = [
        os.path.join(base_dir, "score_search.parquet"),
        os.path.join(base_dir, "Daten", "score_search.parquet")
    ]

#die Datei suchen
    rest_path = next((p for p in possible_paths if os.path.exists(p)), None)

#Falls keiner der beiden Pfade existiert, erscheint eine Fehlermeldung.
    if rest_path is None:
        st.error(
            "score_search.parquet was not found. "
            "Please place the file either in the 'Data' folder next to app.py "
            "or in the same directory as app.py."
        )
        st.stop()

    #datei wird gelesen
    df = pd.read_parquet(rest_path)

# Prüfung und Vereinheitlichung der Spaltennamen.
# Einige Datensätze enthalten alternative Spaltenbezeichnungen (z. B. "name_x"
# anstelle von "name"). Um im weiteren Programmverlauf einheitlich auf die
# Daten zugreifen zu können, werden vorhandene Alternativspalten auf die
# erwarteten Standardnamen abgebildet.

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

    # Kategorien vorbereiten
    #Welche der erwarteten Kategorie-Spalten existieren tatsächlich in der Parquet-Datei?
    available_category_columns = [col for col in category_columns if col in df.columns]
    
    #Kategorien aus One-Hot-Spalten erzeugen
    if available_category_columns:
        df["categories"] = df[available_category_columns].eq(1).apply(
            lambda row: row.index[row].tolist(), #läuft jede Restaurant-Zeile einzeln durch um .
            axis=1
        )
    elif "categories" in df.columns:
        df["categories"] = df["categories"].apply(
            lambda x: x if isinstance(x, list)
            else ([c.strip() for c in str(x).split(",") if c.strip()] if pd.notna(x) else [])
        )
    else:
        df["categories"] = [[] for _ in range(len(df))]

    # Preis: Parquet-Datei hat PriceLevel oder nicht? Wenn ja = true.
    if "PriceLevel" in df.columns:
        df["price"] = df["PriceLevel"].apply(normalize_price)
    elif "price" in df.columns:
        df["price"] = df["price"].apply(normalize_price)
    else:
        df["price"] = "﹩﹩"

    # Bewertung: Parquet-Datei hat stars. Wird für die Anzaige der Ergebnisse benötigt
    if "stars" in df.columns:
        df["rating"] = df["stars"]
    elif "rating" not in df.columns:
        df["rating"] = 0

    # Attribute: Parquet-Datei hat einzelne 0/1-Spalten.
    # Daraus bauen wir wieder ein attributes-Dict, damit alle UI-Filter gleich bleiben.
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

    #falls kein distance gibt, bekommen jedes Restaurant 0.0, falls nicht vorhanden - 0
    if "distance_km" not in df.columns:
        df["distance_km"] = 0.0

    if "review_count" not in df.columns:
        df["review_count"] = 0


    #Öffnungszeiten vorbereiten: falls vorhanden-> über normalize_attr vereinheitlicht, falls nicht {}
    if "hours" in df.columns:
        df["hours"] = df["hours"].apply(normalize_attributes)
    else:
        df["hours"] = [{} for _ in range(len(df))]

    #Adresse vorbereiten-> das gleiche wie bei öffnungszeiten
    if "address" not in df.columns:
        df["address"] = ""

    #Vektoren erzeugen. Dieser Vektor wird später mit dem User-Vektor verglichen.
    df["categories_vector"] = (
        df.reindex(columns=category_columns, fill_value=0)
        .fillna(0)
        .astype(int)
        .values
        .tolist()
    )

    #das gleiche passiert hier
    df["attributes_vector"] = (
        df.reindex(columns=attr_columns, fill_value=0)
        .fillna(0)
        .astype(int)
        .values
        .tolist()
    )

    restaurants_list = df.to_dict(orient="records")
    return df, restaurants_list


#speichert App-Zustände, zum Beispiel:aktuelle Seite, aktueller Standort, ausgewählte Extras,Suchergebnisse.
if (
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
#Hier werden die geografischen Koordinaten des Stadtzentrums von Philadelphia gespeichert.
PHILADELPHIA_CENTER = {"lat": 39.9526, "lon": -75.1652}
PHILADELPHIA_BOUNDS = {
    "min_lat": 39.80,
    "max_lat": 40.10,
    "min_lon": -75.35,
    "max_lon": -74.95,
}
#Ein Geocoder kann Adressen in geografische Koordinaten umwandeln.
geolocator = Nominatim(user_agent="platepilot", timeout=10)

#RESET: Standardwerte der Suchfilter (für reset oder beim ersten laden des apps)
DEFAULT_FILTER_VALUES = {
    "selected_raw": [],
    "selected_kitchen": [],
    "selected_price": "﹩﹩",
    "distance": 10,
    "selected_extras": [],
}

#Standardfilter wiederherstellen (RESET)
def reset_filter_state():
    # Setzt sowohl deine gespeicherten Filter als auch die Streamlit-Widget-Keys zurück.
    # Wichtig: Diese Funktion wird als on_click-Callback ausgeführt, bevor Streamlit
    # die Widgets neu zeichnet. Dadurch werden Preis, Rating und Distance sauber resettet.
    st.session_state["filter_values"] = DEFAULT_FILTER_VALUES.copy()
    st.session_state["selected_extras"] = []

    st.session_state["selected_categories_widget"] = []
    st.session_state["price_widget"] = "﹩﹩"
    st.session_state["dist_slider"] = 10

    # Optional: alte Ergebnisse bleiben nicht mehr als aktive Suche sichtbar.
    st.session_state.pop("results", None)
    st.session_state.pop("filters", None)
    st.session_state["visible_results"] = 20
    st.session_state["alpha_widget"] = 0.6
    st.session_state["w_cat_widget"] = 4.0
    st.session_state["w_attr_widget"] = 3.0
    st.session_state["w_price_widget"] = 2.0
    st.session_state["w_dist_widget"] = 1.0

#Session State: merkt sich Werte pro Nutzer-Session.
#Streamlit führt bei jedem Klick die ganze Datei neu aus. Ohne session_state würde die App alles vergessen. Merkt "results", "selected_extras"
#Aktuelle Seite festlegen
#Hier wird gespeichert, welche Seite der Benutzer gerade sieht. Beim ersten Start gibt es noch keine Seite.
if "page" not in st.session_state:
    st.session_state.page = "form"

if "coords" not in st.session_state:
    st.session_state["coords"] = PHILADELPHIA_CENTER.copy()

#Kartenstatus speichern
if "show_map" not in st.session_state:
    st.session_state["show_map"] = False

#Extras initialisieren
if "selected_extras" not in st.session_state:
    st.session_state["selected_extras"] = []

#Neue Koordinaten
if "new_coords" not in st.session_state:
    st.session_state["new_coords"] = PHILADELPHIA_CENTER.copy()

#Filterwerte initialisieren
if "filter_values" not in st.session_state:
    st.session_state["filter_values"] = DEFAULT_FILTER_VALUES.copy()

# Widgets initialisieren.Jetzt werden die Streamlit-Widgets vorbereitet.
if "selected_categories_widget" not in st.session_state:
    st.session_state["selected_categories_widget"] = st.session_state["filter_values"].get("selected_raw", [])

if "price_widget" not in st.session_state:
    st.session_state["price_widget"] = st.session_state["filter_values"].get("selected_price", "﹩﹩")

#Distanz bekommt den zuletzt gespeiherten Wert
if "dist_slider" not in st.session_state:
    st.session_state["dist_slider"] = st.session_state["filter_values"].get("distance", 10)

# Extras wiederherstellen
#Hier wird geprüft: Sind momentan keine Extras ausgewählt,aber wurden früher welche gespeichert? Falls ja,werden sie wieder in das Widget geladen.
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


#toggle-buttons für additional options
def toggle_extra(extra: str):
    sel = st.session_state["selected_extras"]
    if extra in sel:
        sel.remove(extra)
    else:
        sel.append(extra)


# Formular für den User
# ---------------------------------------------------------

#baut die komplette Startseite der App auf
def show_form(): #baut Startseite

#kein sidebar
    hide_sidebar = """
        <style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="stSidebarNav"] { display: none; }
            .block-container { padding-left: 2rem; padding-right: 2rem; }
        </style>
    """
    st.markdown(hide_sidebar, unsafe_allow_html=True)
    
#Layout erstellen
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

    if stadt is None:
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
        st.caption("Click anywhere on the map to choose your location.")

        m = folium.Map(location=[PHILADELPHIA_CENTER["lat"], PHILADELPHIA_CENTER["lon"]], zoom_start=12)

        #folium.Marker([lat, lon], tooltip="Current Location").add_to(m)
        folium.Marker([lat, lon], tooltip="Your chosen location", icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
        map_data = st_folium(m, height=400, width=700)

        if map_data and map_data.get("last_clicked"):
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lon = map_data["last_clicked"]["lng"]

            st.session_state["new_coords"] = {
                "lat": clicked_lat,
                "lon": clicked_lon
            }

        if "new_coords" in st.session_state:
            new_lat = st.session_state["new_coords"]["lat"]
            new_lon = st.session_state["new_coords"]["lon"]
            new_stadt, new_strasse = reverse_geocode_cached(new_lat, new_lon)

            if new_stadt is None:
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
            st.session_state["coords"] = st.session_state["new_coords"]
            st.session_state["show_map"] = False
            st.success("Location successfully updated!")
            st.rerun()

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
            "🍔 Burgers", "🍟 Fast Food", "🍕 Pizza",
            "🥗 Healthy Options", "🍗 Chicken",
            "🐟 Seafood", "🥪 Sandwiches", "🍜 Noodles", "🍲 Soup",
            "🍰 Desserts", "🥐 Bakeries",
            "🧃 Juice & Smoothies", "🥩 Steak & Barbeque"
        ],
        "🟣 VENUE ─────────────────────────": [
            "🍸 Bars & Nightlife",
            "☕ Coffee & Tea",
            "🍳 Breakfast & Brunch",
            "🍽️ Casual & Quick"
        ]
    }

    #Auswahlliste für die Küchen und Kategorien im Suchformular
    def build_grouped_list(groups: dict):
        items = []
        for header, values in groups.items():
            items.append(header)   # Gruppenüberschrift eingefügt.
            items.extend(values)   # fügt alle Elemente einer Liste hinzu
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
    st.markdown("### 2. Price")

    price_options = ["﹩", "﹩﹩", "﹩﹩﹩", "﹩﹩﹩﹩"]

    # Wichtig: select_slider muss mit einem Tuple starten, damit es ein Range-Slider bleibt.
    # Falls Streamlit vorher nur einen einzelnen String gespeichert hat, reparieren wir den Wert.

    selected_price = st.select_slider(
        "Select preferred price:",
        options= price_options,
        value="﹩﹩",
        key="price_widget"
    )

    st.write(
        f"Selected price: {selected_price}"
    )
    st.markdown("")

    st.markdown("### 3. Distance")
    #Zuerst macht recommendation.py einen schnellen Vorfilter:
    #Restaurants, die grob außerhalb der Gegend liegen, werden direkt entfernt.
    #Dann wird die echte Entfernung berechnet:Je näher das Restaurant ist, desto besser.
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

    st.markdown("### 4. Additional Options")

    extras_list = [
        "Wi-Fi", "Outdoor", "Credit Card", "Reservations", "Takeout",
        "Parking", "Happy Hour", "Dogs Allowed", "TV", "Wheelchair",
        "Alcohol",  "Quiet", "Bike Parking","Good for Kids", "Good for Groups"
    ]

    #Extras in Zeilen aufteilen
    cols_per_row = 5
    rows = [extras_list[i:i + cols_per_row] for i in range(0, len(extras_list), cols_per_row)]

    #Jede Zeile anzeigen, Spalten erzeugen
    for row in rows:
        cols = st.columns(len(row))
        for col, extra in zip(cols, row): #Extras durchlaufen
            with col:
                is_selected = extra in st.session_state["selected_extras"]
                button_type = "primary" if is_selected else "secondary" #button farbe festlegen
                if st.button(
                    f"{'✓ ' if is_selected else ''}{extra}", key=f"chip_{extra}",
                    type=button_type, use_container_width=True
                ):
                    toggle_extra(extra)
                    st.session_state["filter_values"] = {
                        "selected_raw": selected_raw,
                        "selected_kitchen": selected_kitchen,
                        "selected_price": selected_price,
                        "distance": distance,
                        "selected_extras": list(st.session_state["selected_extras"]),
                    }
                    st.rerun()

    sel = st.session_state["selected_extras"]
    if sel:
        st.write(f"**Your preferences:** {', '.join(sel)}")
    
    st.markdown("")
    
    #Block für Advanced Recommendation Settings
    with st.expander("⚙️ Advanced recommendation settings", expanded=False):

        st.markdown(
                """
                <div style="display:flex; justify-content:space-between; margin-bottom:-30px;">
                    <span>🌍 Global</span>
                    <span>🎯 Personal Fit </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        alpha = st.slider("", 0.0, 1.0, 0.6, key="alpha_widget")

        st.markdown(
        """
        <div style="display:flex; justify-content:space-between; margin-bottom:-25px;">
            <span>🍽️ Cuisine Flexible</span>
            <span>👨‍🍳 Strong Cuisine Match</span>
        </div>
        """,
        unsafe_allow_html=True
     )

        w_cat = st.slider("", 0.0, 10.0, 4.0, key="w_cat_widget")

        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; margin-bottom:-25px;">
                <span> 🎁 Extras Optional</span>
                <span> ✅ Must-Have Extras</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        w_attr = st.slider("", 0.0, 10.0, 3.0, key="w_attr_widget")

        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; margin-bottom:-25px;">
                <span>💰 Price Flexible</span>
                <span>🎯 Strict Price Match</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        w_price = st.slider("", 0.0, 10.0, 2.0, key="w_price_widget")

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

        w_dist = st.slider("", 0.0, 10.0, 1.0, key="w_dist_widget")

#CTA Button "Find restaurants"
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔍 Find restaurants", type="primary", use_container_width=False):
        st.session_state["filter_values"] = {
            "selected_raw": selected_raw,
            "selected_kitchen": selected_kitchen,
            "selected_price": selected_price,
           # "use_rating": use_rating,
            "distance": distance,
            "selected_extras": list(st.session_state["selected_extras"]),
            "alpha": alpha,
            "w_cat": w_cat,
            "w_attr": w_attr,
            "w_price": w_price,
           # "price_strict": price_strict,
            "w_dist": w_dist,
        }

        #die aktuell ausgewählten Filter wird gespeichert
        st.session_state["filters"] = {
            "kitchen": selected_kitchen,
            "price_range": selected_price,
           # "use_rating": use_rating,
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

        #Preis in Zahl umwandeln
        price_to_int = {
            "﹩": 1,
            "﹩﹩": 2,
            "﹩﹩﹩": 3,
            "﹩﹩﹩﹩": 4,
        }

        u_price = price_to_int[selected_price]

        #Küchennamen übersetzen
        def clean_label(label):
            return label.split(" ", 1)[1] if label[:1] and not label[0].isalnum() else label
        
        selected_category_names = [
            KITCHEN_MAP.get(k.split(" ", 1)[1] if " " in k else k, k)
            for k in selected_kitchen
        ]

        #app merkt welche Küche der User auswählt und hier wird draus ein Vektor gemacht.1-User möchte diese Kategorie, 0-User möchte nicht
        #Je ähnlicherr Restaurant und User-Wunsch sind, desto höher ist category_score
        #Category vector bauen
        u_cat = [ 
            1 if col in selected_category_names else 0
            for col in category_columns
        ]

        #Additional settings (Extras) normalisieren
        selected_attr_names = [
            normalize_extra_name(x)
            for x in st.session_state["selected_extras"]
        ]

        #Extras auf echte Spaltennamen mappen
        extra_to_column = {
            "Credit Card": "BusinessAcceptsCreditCards",
            "Outdoor Seating": "OutdoorSeating",
            "Reservations": "RestaurantsReservations",
            "Takeout": "RestaurantsTakeOut",
            "Parking": "BusinessParking",
            "Happy Hour": "HappyHour",
            "Dogs Allowed": "DogsAllowed",
            "TV": "HasTV",
            "Wheelchair Accessible": "WheelchairAccessible",
            "Alcohol": "Alcohol",
            "Noise Level": "Quiet",
            "Bike Parking": "BikeParking",
            "Good for Kids": "GoodForKids",
            "Good for Groups": "RestaurantsGoodForGroups",
            "WiFi": "WiFi",
        }

        #Liste mit den tatsächlichen Datenbankspalten, die den ausgewählten Extras entsprechen.
        selected_attr_columns = [
            extra_to_column[x]
            for x in selected_attr_names
            if x in extra_to_column
        ]

        #In recommendation.py wird geprüft:
        #Wie viele gewünschte Extras erfüllt das Restaurant?attribute_score = 2 / 3
        #Extra Vektor bauen
        u_attr = [
            1 if col in selected_attr_columns else 0
            for col in attr_columns
        ]

        #Empfehlungsfunktion aufrufen
        recommended_df = get_recommendations(
            df=df_merged,
            u_cat=u_cat,
            u_attr=u_attr,
            u_price=u_price,
            u_lat=st.session_state["coords"]["lat"],
            u_lon=st.session_state["coords"]["lon"],
            d_max=distance,
            alpha=alpha,
            w_cat=w_cat,
            w_attr=w_attr,
            w_price=w_price,
            w_dist=w_dist,
            top_n=100,
        )

        #Distanz und Score für Anzeige vorbereiten
        recommended_df["distance_km"] = recommended_df["calc_distance"].round(2)
        recommended_df["final_score"] = recommended_df["SCORE"].round(3)

        #DataFrame in Liste von Dictionaries umwandeln
        filtered = recommended_df.to_dict(orient="records")


        #Ergebnisse-Seite vorbereiten (lazy loading = 20)
        st.session_state["visible_results"] = 20
        st.session_state.page = "results" #Die App wechselt von der Suchseite zur Ergebnisseite.
        st.session_state["results"] = filtered #Die berechneten Ergebnisse werden gespeichert.
        st.rerun() #Streamlit startet die App neu.

        
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

    #Anzahl sichtbarer Ergebnisse setzen
    if "visible_results" not in st.session_state:
        st.session_state["visible_results"] = 20

    visible = min(st.session_state["visible_results"], len(results))
    visible_results = results[:visible]

    #Aktive Filter vorbereiten
    f = st.session_state.get("filters", {})
    extras_txt = ", ".join(f.get("extras", [])) or "–" #wandle in text
    kitchen_txt = ", ".join([k for k in f.get("kitchen", [])]) or "–"
    price_txt = f.get("price_range", "﹩﹩")
    dist_txt = "any" if f.get("distance", 0) == 0 else f"up to {f.get('distance')} km"
    #rating_txt = "4 stars and up" if f.get("use_rating") else "all"

    st.markdown(
        f"**Active Filters:** Cuisine: {kitchen_txt} | Price: {price_txt} | Distance: {dist_txt} | Extras: {extras_txt}"
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

            address = r.get("address", "")

            if address:
                st.markdown(f"**Address:** {address}")
            else:
                st.markdown("**Address:** No address available")

            #öffnungszeiten vorbereiten
            st.subheader("Opening Hours")
            hours_data = normalize_attributes(r.get("hours", {}))
            #Prüfen, ob Öffnungszeiten vorhanden sind
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

            #Reihenfolge der Tage festlegen
                day_order = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday"
                ]

            #Öffnungszeiten sammeln
                opening_hours = []

                for day in day_order:

                    if day not in hours_data:
                        continue

                    hours = hours_data[day]

            #Ungültige Öffnungszeiten ignorieren
                    if (
                        not hours
                        or hours == "None"
                        or hours == "0:0-0:0"
                        or hours == "0:00-0:00"
                    ):
                        continue

            #Ausgabe vorbereiten
                    short_day = day_map.get(day, day)

                    opening_hours.append(
                        f"{short_day}: {format_opening_hours(hours)}"
                    )

                if opening_hours:
                    st.write(" | ".join(opening_hours))
                else:
                    st.write("No opening hours available.")

            else:
                st.write("No opening hours available.")

        #Restaurant Preferences / Extras
            st.subheader("Restaurant Preferences")
            extras_list = []
            attr = normalize_attributes(r.get("attributes", {}))

        #attr prüfen und extras hinzufügen
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

            #Ausgewählte User-Extras holen

            selected_extras = st.session_state.get("filters", {}).get("extras", [])

            #Passende Extras finden
            matched = [
                e for e in selected_extras
                if normalize_extra_name(e) in [normalize_extra_name(x) for x in extras_list]
            ]

            #Weitere vorhandene Extras finden
            other = [
                e for e in extras_list
                if e not in matched
            ]

            #Passende Wünsche anzeigen
            if matched:
                st.markdown("**Matched Preferences**")
                st.write(", ".join(f"✓ {x}" for x in matched))

            #Zusätzliche Features anzeigen
            if other:
                st.markdown("**Additional Features**")
                st.write(", ".join(other))

            #Falls keine Extras vorhanden sind
            if not matched and not other:
                st.write("No extras available.")

            # NUR ZUM TESTEN: Debug Scores anzeigen
            st.markdown("---")
            st.markdown("**Debug Scores**")

            st.write(f"Category Score: {r.get('category_score')}")
            st.write(f"Attribute Score: {r.get('attribute_score')}")
            st.write(f"Price Score: {r.get('price_score')}")
            st.write(f"Distance Score: {r.get('distance_score')}")
            st.write(f"Popularity Score: {r.get('popularity_score')}")
            st.write(f"Final Score: {r.get('final_score')}")


            st.markdown("")

            #Google-Maps-Link erstellen
            address = r.get("address", "")
            maps_query = quote_plus(address if address else r.get("name", ""))

            maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_query}"

            st.link_button("📍 Route", maps_url)

#ob noch Ergebnisse übrig sind?
    if visible < len(results):
        st.markdown("")
        remaining = len(results) - visible #Freie Anzahl berechnen:wieviele Restaurants noch nicht angezeigt werden: 100-20=80
        next_batch = min(20, remaining) #nächste block von lazy loading

        if st.button(
            f"Load {next_batch} more restaurants ({visible}/{len(results)})",
            use_container_width=True
        ):
    #Anzahl sichtbarer Ergebnisse erhöhen
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