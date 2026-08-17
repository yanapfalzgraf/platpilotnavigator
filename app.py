"""
PlatePilot Navigator – Streamlit-Anwendung für Restaurantempfehlungen.

ÜBERBLICK
---------
Diese Datei bildet die Benutzeroberfläche und die Ablaufsteuerung der App ab.

Datenfluss:
1. ``score_search.parquet`` wird geladen und in ein einheitliches Format gebracht.
2. Nutzereingaben (Küche, Preis, Distanz und Extras) werden im ``st.session_state`` gespeichert.
3. Aus den Eingaben werden Kategorie- und Attributvektoren erzeugt.
4. ``recommendation.py`` berechnet über ``get_recommendations(...)`` die Restaurant-Scores.
5. Die Ergebnisse werden auf der zweiten Seite sortiert, paginiert und dargestellt.

SEITEN
------
- ``show_form()``: Seite 1 – Standort und Restaurantpräferenzen auswählen.
- ``show_results()``: Seite 2 – gerankte Restaurantempfehlungen anzeigen.

WICHTIGE BEREICHE
-----------------
- Mapping-Tabellen: Übersetzen UI-Bezeichnungen in Daten-/Modellspalten.
- Datenvorbereitung: Vereinheitlicht Kategorien, Attribute, Preise und weitere Spalten.
- Session State: Hält Filter, Standort und Ergebnisse über Streamlit-Reruns hinweg.
- UI-Helfer: Laden Bilder, erzeugen Header/Stepper und injizieren das CSS.
- Recommendation Bridge: Übersetzt die UI-Auswahl in die Eingaben für recommendation.py.
- Routing: Entscheidet, welche der beiden Seiten angezeigt wird.

Hinweis:
Streamlit führt dieses Skript bei Interaktionen erneut von oben nach unten aus.
Deshalb werden persistente UI-Zustände über ``st.session_state`` verwaltet.
"""

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
from pathlib import Path
import base64
import html

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
    """Übersetzt die im UI verwendete Extra-Bezeichnung in den internen Namen.
    
        Unbekannte Werte werden unverändert zurückgegeben, damit die Funktion robust
        gegenüber später ergänzten Optionen bleibt.
        
    """
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
    """Liest aus einer Restaurantzeile alle aktiven One-Hot-Kategorien aus.
    
        Eine Kategorie gilt als aktiv, wenn die entsprechende Spalte den Wert 1 besitzt.
        
    """
    return [col for col in category_columns if row.get(col, 0) == 1]#Hier wird aus der aktuellen Zeile ein Wert gelesen.

#In einer Parquet-Datei können Attribute unterschiedlich gespeichert sein.
#Die Funktion sorgt dafür, dass am Ende immer ein Dictionary herauskommt.
def normalize_attributes(attr): #Attribute müssen immer als dict vorliegen
    """Vereinheitlicht Restaurantattribute zu einem Dictionary.
    
        Die Parquet-Daten können Attribute bereits als ``dict`` oder als String enthalten.
        Nicht interpretierbare Werte werden sicher als leeres Dictionary behandelt.
        
    """
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
    """Gleicht unterschiedliche Attributnamen aus Datenquelle und UI an.
    
        Dadurch können spätere Programmteile immer mit denselben internen Schlüsseln arbeiten.
        
    """
    attr = normalize_attributes(attr)

    if "RestaurantsGoodForGroups" in attr and "GoodForGroups" not in attr:
        attr["GoodForGroups"] = attr.get("RestaurantsGoodForGroups")

    # Parquet-Spalte Quiet wird für Lautstärke genutzt.
    if "Quiet" in attr and "NoiseLevel" not in attr:
        attr["NoiseLevel"] = "quiet" if truthy_attr(attr.get("Quiet")) else None

    return attr

#sorgt dafür, dass all diese unterschiedlichen Darstellungen einheitlich als True erkannt werden.
def truthy_attr(value): 
    """Interpretiert verschiedene Datenrepräsentationen als booleschen Attributwert.
    
        Unterstützt unter anderem True/False, 1/0 sowie typische Stringwerte wie
        ``yes``, ``free``, ``paid`` oder ``full_bar``.
        
    """
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
    """Normalisiert unterschiedliche Preisangaben auf vier Preisstufen.
    
        Fehlende oder unbekannte Werte werden als mittlere Standardstufe ``﹩﹩`` behandelt.
        
    """
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
    """Formatiert Öffnungszeiten im Format ``HH:MM-HH:MM``.
    
        Falls der Eingangswert nicht dem erwarteten Format entspricht, wird er unverändert
        zurückgegeben.
        
    """
    try:
        start, end = str(hours).split("-")
        sh, sm = start.split(":")
        eh, em = end.split(":")
        return f"{int(sh):02d}:{int(sm):02d}-{int(eh):02d}:{int(em):02d}"
    except Exception:
        return str(hours)
        
# =========================================================
# DATENQUELLE, CACHE UND DATEIPFADE
# =========================================================
#Die Restaurantdaten werden nicht bei jedem Klick neu geladen.
#Streamlit merkt sich das geladene DataFrame. Das macht die App schneller. 
@st.cache_data(show_spinner="Loading restaurant data...") 

#Die Datei score_search.parquet finden.
#Die Daten laden und vorbereiten.
def load_and_prepare_data(): #sucht die Datei:restaurant_filter.parquet
    """Lädt ``score_search.parquet`` und bereitet sie für UI und Ranking vor.
    
        Die Funktion:
        - sucht die Datei an den unterstützten Speicherorten,
        - vereinheitlicht alternative Spaltennamen,
        - erzeugt Kategorien- und Attribut-Dictionaries,
        - normalisiert Preis, Rating, Öffnungszeiten und Adresse,
        - erzeugt Kategorie- und Attributvektoren für das Empfehlungssystem.
    
        Das Ergebnis wird mit ``st.cache_data`` gecacht, damit die Datei nicht bei jedem
        Streamlit-Rerun erneut eingelesen werden muss.
        
    """
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
    if "stars_real" in df.columns:
        df["rating"] = df["stars_real"]
    elif "stars" in df.columns:
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


# =========================================================
# APP-ZUSTAND UND STANDARDWERTE
# =========================================================
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
    """Setzt alle Suchfilter und zugehörigen Widget-Zustände zurück.
    
        Zusätzlich werden alte Suchergebnisse entfernt und die Gewichtungsparameter auf
        ihre Standardwerte gesetzt.
        
    """
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


# =========================================================
# STANDORT- UND UI-HILFSFUNKTIONEN
# =========================================================
#Mit reverse_geocode() wird aus Koordinaten eine Adresse gemacht.
def reverse_geocode(lat, lon):
    """Wandelt geografische Koordinaten in Stadt und Straße um.
    
        Bei Netzwerk-/Geocoding-Fehlern wird ``(None, None)`` zurückgegeben.
        
    """
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
    """Gecachte Variante von ``reverse_geocode``.
    
        Das Ergebnis bleibt eine Stunde im Streamlit-Cache und reduziert dadurch unnötige
        Anfragen an den Geocoding-Dienst.
        
    """
    return reverse_geocode(lat, lon)


#toggle-buttons für additional options
def toggle_extra(extra: str):
    """Schaltet eine zusätzliche Restaurantoption im Session State ein oder aus.
    """
    sel = st.session_state["selected_extras"]
    if extra in sel:
        sel.remove(extra)
    else:
        sel.append(extra)


def clear_cuisine_selection():
    """Leert ausschließlich die Auswahl des Cuisine-/Food-Multiselects."""
    st.session_state["selected_categories_widget"] = []




# =========================================================
# PLATEPILOT-DESIGN: ASSETS, CSS UND GEMEINSAME UI-BAUSTEINE
import re
# =========================================================

BASE_DIR = Path(__file__).parent


def _find_asset(*candidates):
    """Findet das erste vorhandene Asset relativ zu app.py."""
    for candidate in candidates:
        path = BASE_DIR / candidate
        if path.is_file():
            return path

    # Fallback: Windows blendet Dateiendungen häufig aus.
    # Deshalb suchen wir zusätzlich nach Dateien mit passendem Stammnamen.
    wanted_stems = {Path(candidate).stem.lower() for candidate in candidates}

    for folder in (BASE_DIR, BASE_DIR / "Bilder", BASE_DIR / "bilder"):
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.stem.lower() in wanted_stems:
                return path

    return None


def _data_url(path):
    """Konvertiert ein lokales Bild in eine Base64-Data-URL für eingebettetes HTML.
    """
    if path is None or not path.is_file():
        return ""
    suffix = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


LOGO_PATH = _find_asset(
    "platepilot.png",
    "Bilder/platepilot.png",
    "Bilder/logo.png",
)

HERO_PATH = _find_asset(
    "gericht.png",
    "gericht.jpg",
    "gericht.jpeg",
    "gericht.webp",
)

LOGO_URL = _data_url(LOGO_PATH)
HERO_URL = _data_url(HERO_PATH)

#--DESIGN DES DROPDOWNS--#

def inject_platepilot_css():
    
    """Injiziert das komplette PlatePilot-Design als CSS in die Streamlit-Seite.
    
        Hier werden unter anderem Header, Stepper, Formulare, Buttons, Ergebnislisten,
        Dropdowns und das responsive Verhalten definiert.
        
    """
    st.html(
        """
        <style>
        :root {
            --pp-bg: #06101b;
            --pp-bg-2: #091523;
            --pp-panel: #0d1928;
            --pp-panel-2: #101d2d;
            --pp-line: #2a3950;
            --pp-text: #f7f9fd;
            --pp-muted: #aeb8c8;
            --pp-blue: #4f8dff;
            --pp-purple: #8a4dff;
            --pp-green: #43e27a;
            --pp-gold: #ffc341;
            --pp-danger: #ff424e;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background:
                radial-gradient(circle at 76% -5%, rgba(55, 99, 170, .13), transparent 33%),
                linear-gradient(180deg, #050d16 0%, #06101b 60%, #040a12 100%) !important;
            color: var(--pp-text);
        }

        [data-testid="stHeader"] { background: transparent !important; }
        [data-testid="stToolbar"] { visibility: hidden !important; }
        [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; }

        .block-container {
            max-width: 1540px !important;
            padding: 0.7rem 1.5rem 3rem !important;
        }

     
        /* ---------- Header ---------- */
        .pp-header {
            position: relative;
            min-height: 390px;
            overflow: hidden;
            border: 1px solid var(--pp-line);
            border-radius: 26px;
            background:
                radial-gradient(circle at 24% 42%, rgba(78, 72, 210, .11), transparent 35%),
                linear-gradient(135deg, #07111d 0%, #081421 58%, #07111d 100%);
            box-shadow:
                inset 0 0 0 1px rgba(255,255,255,.012),
                0 18px 55px rgba(0,0,0,.16);
        }

        /* dezente grafische Linien wie im neuen Hero-Design */
        .pp-header::before {
            content: "";
            position: absolute;
            z-index: 1;
            left: -4%;
            bottom: -18%;
            width: 66%;
            height: 82%;
            opacity: .42;
            pointer-events: none;
            background:
                radial-gradient(ellipse at 34% 60%,
                    transparent 0 43%,
                    rgba(103,80,255,.24) 43.5% 44%,
                    transparent 44.5% 52%,
                    rgba(69,104,255,.14) 52.5% 53%,
                    transparent 53.5% 61%,
                    rgba(126,68,255,.12) 61.5% 62%,
                    transparent 62.5%);
        }

        .pp-header-photo {
            position: absolute;
            z-index: 0;
            top: 0;
            right: 0;
            bottom: 0;
            width: 53%;
            background-size: cover;
            background-position: right center;
            background-repeat: no-repeat;
        }

        .pp-header-overlay {
            position: absolute;
            z-index: 1;
            inset: 0;
            background:
                linear-gradient(
                    90deg,
                    #06101b 0%,
                    #06101b 32%,
                    rgba(6,16,27,.97) 42%,
                    rgba(6,16,27,.72) 52%,
                    rgba(6,16,27,.25) 67%,
                    rgba(6,16,27,.03) 100%
                ),
                linear-gradient(
                    0deg,
                    rgba(5,13,22,.72) 0%,
                    rgba(5,13,22,.06) 36%,
                    rgba(5,13,22,0) 100%
                );
        }

        /*
          Brand-Lockup:
          Logo und Name bilden jetzt optisch EINE Einheit.
        */
        .pp-header-content {
            position: relative;
            z-index: 3;
            display: grid;
            grid-template-columns: 132px minmax(260px, 470px);
            align-items: start;
            column-gap: 1.65rem;
            width: 59%;
            min-height: 242px;
            padding: 2.55rem 3.35rem 1.1rem;
        }

        .pp-logo-shell {
            width: 132px;
            height: 132px;
            display: grid;
            place-items: center;
            border: 1px solid rgba(116, 95, 255, .55);
            border-radius: 30px;
            background:
                radial-gradient(circle at 42% 35%, rgba(83,111,255,.16), transparent 55%),
                rgba(9,20,34,.82);
            box-shadow:
                inset 0 0 0 1px rgba(255,255,255,.025),
                0 14px 35px rgba(0,0,0,.22),
                0 0 28px rgba(92,72,232,.08);
            backdrop-filter: blur(4px);
        }

        .pp-logo {
            width: 92px;
            height: 92px;
            object-fit: contain;
            display: block;
        }

        .pp-brand {
            min-width: 0;
        }

        .pp-brand h1 {
            margin: 0;
            color: white;
            font-size: clamp(2.8rem, 4.35vw, 4.65rem);
            line-height: .93;
            font-weight: 820;
            letter-spacing: -.055em;
            text-shadow: 0 6px 28px rgba(0,0,0,.18);
        }

        .pp-brand h1 span {
            background: linear-gradient(
                90deg,
                #4698ff 0%,
                #627cff 42%,
                #8b56ff 78%,
                #aa4eff 100%
            );
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .pp-brand p {
            margin: 1.1rem 0 0;
            color: #b7c2d2;
            font-size: 1.08rem;
            line-height: 1.45;
            letter-spacing: .005em;
        }

        
        /* ---------- Clean 2-step navigation ---------- */

        .pp-progress {
            position: absolute;
            z-index: 4;

            left: 14%;
            bottom: 1.65rem;

            /* Rahmen passt sich exakt an den Inhalt an */
            width: fit-content;
            min-height: 84px;

            display: flex;
            align-items: center;

            padding: 0 1.25rem;

            border: 1px solid rgba(61, 80, 108, .78);
            border-radius: 18px;

            background: linear-gradient(
                135deg,
                rgba(14, 28, 45, .96),
                rgba(8, 19, 32, .94)
            );

            box-shadow:
                0 12px 30px rgba(0,0,0,.18),
                inset 0 0 0 1px rgba(255,255,255,.018);

            backdrop-filter: blur(7px);
        }

        .pp-step {
            position: relative;

            display: flex;
            align-items: center;
            gap: .78rem;

            flex: 0 0 auto;

            min-width: 0;

            text-align: left;
            color: #aeb8c8;
        }

        /* Sichtbare Verbindungslinie genau zwischen Step 1 und Step 2 */
        .pp-step:first-child::after {
            content: "";

            display: block;
            flex: 0 0 72px;

            width: 72px;
            height: 2px;

            margin-left: 26px;
            margin-right: 26px;

            border-radius: 999px;

            background: linear-gradient(
                90deg,
                #8a4dff 0%,
                #6f77ff 55%,
                #4f8dff 100%
            );

            box-shadow: 0 0 8px rgba(111, 119, 255, .18);
        }

        .pp-step-circle {
            flex: 0 0 46px;

            width: 46px;
            height: 46px;

            display: grid;
            place-items: center;

            margin: 0;

            border: 1.5px solid #56657c;
            border-radius: 50%;

            background: #101d2d;
            color: #e1e8f4;

            font-size: 1rem;
            font-weight: 750;

            box-shadow: 0 6px 16px rgba(0,0,0,.20);
        }

        .pp-step.active .pp-step-circle {
            border: 2px solid #9563ff;

            background: linear-gradient(
                135deg,
                #5545c8,
                #8b46db
            );

            color: white;

            box-shadow: 0 0 18px rgba(139,70,219,.38);
        }

        .pp-step.done .pp-step-circle {
            border: 1.5px solid #4f8dff;

            background: linear-gradient(
                135deg,
                #163b74,
                #13284e
            );

            color: white;
        }

        .pp-step-text {
            min-width: 0;

            display: flex;
            flex-direction: column;
            justify-content: center;

            gap: .16rem;
        }

        .pp-step-label {
            margin: 0;

            color: #f4f7fb;

            font-size: .94rem;
            font-weight: 750;
            line-height: 1.2;

            white-space: nowrap;
        }

        .pp-step-subtitle {
            margin: 0;

            color: #9eabba;

            font-size: .78rem;
            font-weight: 400;
            line-height: 1.25;

            white-space: nowrap;
        }

        .pp-step.active .pp-step-label {
            color: #ffffff;
        }


        /* ---------- Common panels ---------- */
        .pp-card {
            border: 1px solid var(--pp-line);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(15,28,44,.96), rgba(8,17,29,.97));
            box-shadow: 0 16px 45px rgba(0,0,0,.10);
        }

        .pp-title-row {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .pp-round-icon {
            width: 64px;
            height: 64px;
            flex: 0 0 64px;
            display: grid;
            place-items: center;
            border: 1px solid #6e45dc;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(69,90,210,.26), rgba(67,34,110,.22));
            font-size: 1.8rem;
        }

        .pp-section-title {
            margin: 0;
            color: white;
            font-size: 1.75rem;
            font-weight: 800;
        }

        .pp-section-subtitle {
            margin: .35rem 0 0;
            color: var(--pp-muted);
            font-size: 1rem;
        }

        /* ---------- User + prompt cards ---------- */
        .st-key-user_card {
            border: 1px solid var(--pp-line);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(15,28,44,.96), rgba(8,17,29,.97));
            padding: 1.45rem 1.8rem;
            margin-top: .85rem;
        }

        /* Intro + Filter in EINEM gemeinsamen Block */
        .st-key-main_form_card {
            border: 1px solid var(--pp-line);
            border-left: 3px solid var(--pp-purple);
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(14,27,43,.98), rgba(7,16,28,.98));
            padding: 1.45rem 1.7rem 1.7rem;
            margin-top: 1.2rem;
            box-shadow: 0 18px 45px rgba(0,0,0,.12);
        }
            .pp-form-divider {
            height: 0;
            margin: 1.2rem 0 1.2rem;

            border: none;
            border-top: 1px dashed rgba(88, 105, 130, 0.4);
        }

      

        .pp-user-title {
            margin: 0;
            color: white;
            font-size: 1.72rem;
            font-weight: 800;
        }

        .pp-user-sub {
            margin: .45rem 0 0;
            color: var(--pp-muted);
            font-size: 1rem;
        }

        .pp-location {
            color: white;
            font-size: 1rem;
            line-height: 1.45;

            border-left: 1px solid #2a3950;
            padding-left: 2rem;
            min-height: 92px;

            display: flex;
            align-items: center;
        }

        /* ---------- Streamlit controls ---------- */
        /* Select-Styles stehen gesammelt im Dropdown-Block weiter unten. */

        /* ---------- Slider ---------- */
        div[data-testid="stSlider"] {
            color: #dce5f3 !important;
        }

        div[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
            background: #ff4b55 !important;
            border-color: #ff4b55 !important;
            box-shadow: 0 0 0 1px rgba(255,75,85,.15) !important;
        }

        div[data-testid="stSlider"] [data-baseweb="slider"] > div > div {
            background: #344157 !important;
        }

        div[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div {
            background: #ff4b55 !important;
        }

        /* ---------- Expander ---------- */
        div[data-testid="stExpander"] details {
            background: #0a1624 !important;
            border-radius: 12px !important;
        }

        div[data-testid="stExpander"] summary {
            color: #e8edf7 !important;
            background: #0a1624 !important;
            border-radius: 12px !important;
        }

        div[data-testid="stExpander"] summary:hover {
            background: #101e30 !important;
        }

        div[data-testid="stExpander"] summary svg {
            fill: #b9c5d8 !important;
            color: #b9c5d8 !important;
        }

        /* ---------- Inputs / Number inputs / Text inputs ---------- */
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextArea"] textarea {
            color: #edf2fb !important;
            background: #101c2d !important;
            border-color: #3c4d67 !important;
        }

        div[data-testid="stTextInput"] input::placeholder,
        div[data-testid="stTextArea"] textarea::placeholder {
            color: #7f8ca0 !important;
        }

        /* ---------- Checkbox / Radio / Toggle ---------- */
        div[data-testid="stCheckbox"] label,
        div[data-testid="stRadio"] label,
        div[data-testid="stToggle"] label {
            color: #dce5f3 !important;
        }

        div[data-testid="stCheckbox"] input:checked + div,
        div[data-testid="stToggle"] input:checked + div {
            background: #6549ef !important;
            border-color: #806bff !important;
        }

        /* ---------- Tooltips ---------- */
        div[data-baseweb="tooltip"],
        div[role="tooltip"] {
            color: #eef3fb !important;
            background: #101c2d !important;
            border: 1px solid #354760 !important;
        }

        /* ---------- Dialog / Modal ---------- */
        div[role="dialog"] {
            color: #e9eef8 !important;
            background: #081421 !important;
            border: 1px solid #33445e !important;
        }

        div[data-testid="stButton"] button,
        div[data-testid="stLinkButton"] a {
            min-height: 44px;
            font-size: .875rem !important;   /* 14px */
            border-radius: 11px !important;
            border: 1px solid #41516a !important;
            background: #0f1a2a !important;
            color: #edf2fb !important;
            font-weight: 600 !important;
        }

        div[data-testid="stButton"] button:hover,
        div[data-testid="stLinkButton"] a:hover {
            border-color: #6b72ff !important;
            background: #15243a !important;
        }

        button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            border-color: #7055ff !important;
            background: linear-gradient(100deg, #7134df, #315ee4) !important;
            color: white !important;
        }

        button[kind="primary"] * { color: white !important; }

        /* ---------- Preference page ---------- */
        .pp-filter-head {
            margin: 1.25rem 0 .7rem;
            color: white;
            font-size: 1.55rem;
            font-weight: 800;
        }

        .pp-filter-caption {
            margin: 0 0 .65rem;
            color: var(--pp-muted);
            font-size: .9rem;       /* ca. 14.4 px */
            line-height: 1.4;
        }

        .pp-tip {
            margin: 1rem 0;
            padding: .9rem 1rem;
            border: 1px solid #30405a;
            border-left: 3px solid var(--pp-purple);
            border-radius: 11px;
            background: rgba(15,28,44,.82);
            color: #b8c3d4;
        }

        [class*="st-key-chip_"] button {
            min-height: 43px !important;
            border-radius: 10px !important;
        }

        /* ---------- Results layout ---------- */
        .st-key-results_shell > div[data-testid="stVerticalBlock"] {
            gap: .5rem;
        }

        .st-key-results_sidebar,
        .st-key-results_main {
            border: 1px solid var(--pp-line);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(14,27,43,.98), rgba(7,16,28,.98));
            padding: 1.25rem;
        }

                /* CTA: Edit preferences */
        .st-key-results_sidebar button[kind="primary"],
        .st-key-results_sidebar button[data-testid="baseButton-primary"] {
            min-height: 50px !important;

            background: linear-gradient(
                100deg,
                #5D4BED 0%,
                #4366EA 100%
            ) !important;

            border: 1px solid #8173FF !important;
            border-radius: 11px !important;

            color: #FFFFFF !important;
            font-weight: 700 !important;

            box-shadow:
                0 8px 24px rgba(91, 76, 237, 0.25),
                0 0 0 1px rgba(255,255,255,.03) inset !important;
        }

        .st-key-results_sidebar button[kind="primary"]:hover,
        .st-key-results_sidebar button[data-testid="baseButton-primary"]:hover {
            background: linear-gradient(
                100deg,
                #6D5AF7 0%,
                #4D6FF2 100%
            ) !important;

            border-color: #A096FF !important;

            box-shadow:
                0 10px 30px rgba(91, 76, 237, 0.38),
                0 0 0 3px rgba(129, 115, 255, 0.10) !important;

            transform: translateY(-1px);
        }

        .pp-side-head {
            padding-bottom: 1rem;
            border-bottom: 1px solid #2c394c;
        }

        .pp-side-head h3,
        .pp-results-head h2 {
            margin: 0;
            color: white;
            font-size: 1.35rem;
            font-weight: 800;
        }

        .pp-side-head p,
        .pp-results-head p {
            margin: .25rem 0 0;
            color: var(--pp-muted);
        }

        .pp-summary-block {
            padding: 1rem 0;
            border-bottom: 1px solid #2a374a;
        }

        .pp-summary-label {
            color: #f3f6fb;
            font-size: 1rem;
            font-weight: 700;
        }

        .pp-summary-value {
            margin-top: .4rem;
            color: #c3ccda;
            line-height: 1.5;
        }

        .pp-count {
            display: flex;
            align-items: baseline;
            gap: .7rem;
            padding: 1.1rem 0 .2rem;
        }

        .pp-count strong {
            color: #9758ff;
            font-size: 2.2rem;
        }

        .pp-count span {
            color: #b8c2d0;
            font-size: .86rem;
        }

        .pp-results-toolbar {
            margin-bottom: .8rem;
        }

        .pp-result-card {
            margin: .7rem 0;
            padding: 1rem 1.05rem;
            border: 1px solid #2a394d;
            border-radius: 14px;
            background: linear-gradient(100deg, #0f1d2d, #091522);
        }

        /* Restaurant card: summary + View details as one visual block */
        [class*="st-key-restaurant_card_"] {
            margin: .3rem 0;
            padding: 1rem 1.05rem .75rem;
            border: 1px solid #2a394d;
            border-radius: 14px;
            background: linear-gradient(100deg, #0f1d2d, #091522);
        }

        [class*="st-key-restaurant_card_"] .pp-result-content {
            margin: 0;
            padding: 0;
        }

        [class*="st-key-restaurant_card_"] div[data-testid="stExpander"] {
            margin-top: .85rem;
            border: none !important;
            border-top: 1px dashed rgba(70, 87, 110, .55) !important;
            border-radius: 0 !important;
            background: transparent !important;
        }

        [class*="st-key-restaurant_card_"] div[data-testid="stExpander"] details,
        [class*="st-key-restaurant_card_"] div[data-testid="stExpander"] summary {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
        }

        [class*="st-key-restaurant_card_"] div[data-testid="stExpander"] summary {
            padding-left: 0 !important;
            padding-right: 0 !important;
        }


        /* Per-restaurant Directions action */
        [class*="st-key-restaurant_card_"] div[data-testid="stLinkButton"] {
            margin-top: .8rem;
            margin-bottom: .15rem;
        }

        [class*="st-key-restaurant_card_"] div[data-testid="stLinkButton"] a {
            width: fit-content !important;
            min-height: 38px !important;
            padding: .45rem .85rem !important;
            border-radius: 9px !important;
            border: 1px solid #3b4d68 !important;
            background: rgba(15, 26, 42, .72) !important;
            color: #e9eef8 !important;
            font-weight: 600 !important;
        }

        [class*="st-key-restaurant_card_"] div[data-testid="stLinkButton"] a:hover {
            border-color: #6b72ff !important;
            background: #15243a !important;
        }


        .pp-result-name {
            color: white;
            font-size: 1.24rem;
            font-weight: 800;
        }

        .pp-result-meta {
            margin-top: .25rem;
            color: #c4ccda;
            font-size: .91rem;
        }

        .pp-score {
            color: #FFFFFF;
            font-weight: 700;
        }

        .pp-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: .35rem;
            margin-top: .65rem;
        }

        .pp-mini-chip {
            padding: .25rem .5rem;
            border: 1px solid #334257;
            border-radius: 7px;
            color: #d6dde9;
            background: #0c1725;
            font-size: .76rem;
        }

        .pp-progress-bar {
            height: 5px;
            margin-top: .45rem;
            overflow: hidden;
            border-radius: 999px;
            background: #273448;
        }

        .pp-progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #914fff, #6f77ff);
        }

        div[data-testid="stExpander"] {
            border: 1px solid #2a394d !important;
            border-radius: 12px !important;
            background: #0a1624 !important;
        }

        /* CTA: Find restaurants – gleich wie Edit preferences */
        .st-key-find_restaurants_cta button[kind="primary"],
        .st-key-find_restaurants_cta button[data-testid="baseButton-primary"] {
            min-height: 50px !important;

            background: linear-gradient(
                100deg,
                #5D4BED 0%,
                #4366EA 100%
            ) !important;

            border: 1px solid #8173FF !important;
            border-radius: 11px !important;

            color: #FFFFFF !important;
            font-weight: 700 !important;

            box-shadow:
                0 8px 24px rgba(91, 76, 237, 0.25),
                0 0 0 1px rgba(255,255,255,.03) inset !important;
        }

        .st-key-find_restaurants_cta button[kind="primary"]:hover,
        .st-key-find_restaurants_cta button[data-testid="baseButton-primary"]:hover {
            background: linear-gradient(
                100deg,
                #6D5AF7 0%,
                #4D6FF2 100%
            ) !important;

            border-color: #A096FF !important;

            box-shadow:
                0 10px 30px rgba(91, 76, 237, 0.38),
                0 0 0 3px rgba(129, 115, 255, 0.10) !important;

            transform: translateY(-1px);
        }

        /* ---------- Mobile ---------- */
        @media (max-width: 900px) {
            .block-container { padding: .55rem .8rem 2rem !important; }
            .pp-header {
                min-height: 390px;
            }
            .pp-header-photo {
                inset: 0;
                width: 100%;
                opacity: .27;
            }
            .pp-header-overlay {
                background: linear-gradient(
                    90deg,
                    rgba(6,16,27,.98),
                    rgba(6,16,27,.88) 58%,
                    rgba(6,16,27,.48)
                );
            }
            .pp-header-content {
                width: 100%;
                grid-template-columns: 86px 1fr;
                column-gap: 1rem;
                min-height: 245px;
                padding: 0.5rem 1.35rem 1rem;
            }
            .pp-logo-shell {
                width: 86px;
                height: 86px;
                border-radius: 10px;
            }
            .pp-logo {
                width: 62px;
                height: 62px;
            }
            .pp-brand h1 {
                font-size: clamp(2.2rem, 10vw, 3.45rem);
            }
            .pp-brand p {
                margin-top: .75rem;
                font-size: .9rem;
            }

            .pp-progress {
                left: 3%;
                right: auto;
                bottom: 1.25rem;

                width: fit-content;
                max-width: 94%;

                padding: 0 .9rem;
            }

            .pp-step {
                gap: .55rem;
            }

            .pp-step:first-child::after {
                flex-basis: 34px;
                width: 34px;
                margin-left: 12px;
                margin-right: 12px;
            }

            .pp-step-circle {
                flex-basis: 40px;
                width: 40px;
                height: 40px;
            }

            .pp-step-label {
                font-size: .78rem;
            }

            .pp-step-subtitle {
                font-size: .68rem;
            }

        }

        /* ---------- Footer underneath the closed multiselect ---------- */
        .pp-cuisine-footer {
            min-height: 34px;
            margin-top: .45rem;

            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }

        .pp-cuisine-count {
            color: #8f9caf;
            font-size: .78rem;
        }

        /* Clear button is deliberately small and link-like. */
        .st-key-clear_cuisine button {
            width: auto !important;
            min-height: 32px !important;

            padding: .25rem .7rem !important;

            border-color: transparent !important;
            background: transparent !important;

            color: #a774ff !important;
            font-size: .78rem !important;
            font-weight: 650 !important;

            box-shadow: none !important;
        }

        .st-key-clear_cuisine button:hover {
            background: rgba(138,77,255,.08) !important;
            border-color: rgba(138,77,255,.16) !important;
            color: #c09cff !important;
        }

        /* =========================================================
           PLATEPILOT DROPDOWNS – ZENTRALER, BEREINIGTER CSS-BLOCK
           ========================================================= */

        :root {
            --pp-dd-bg: #081522;
            --pp-dd-bg-hover: #12233a;
            --pp-dd-border: #31435b;
            --pp-dd-border-hover: #59658b;
            --pp-dd-border-focus: #8a4dff;
            --pp-dd-text: #f4f7fb;
            --pp-dd-muted: #9aa8bb;
            --pp-dd-chip-bg: #102238;
            --pp-dd-chip-border: #2e4866;
        }

        /* FOOD / CUISINE – geschlossen */
        .st-key-selected_categories_widget [data-baseweb="select"] {
            position: relative !important;
            min-height: 56px !important;
            color-scheme: dark !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"] > div {
            min-height: 56px !important;
            padding: 6px 30px 6px 40px !important;
            background: linear-gradient(180deg, rgba(12,30,48,.98), rgba(7,21,34,.98)) !important; /*geschlossenes großes dropdown*/
            border: 1px solid var(--pp-dd-border) !important;
            border-radius: 10px !important;
            color: var(--pp-dd-text) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.018), 0 5px 16px rgba(0,0,0,.08) !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"]::before {
            content: "🍴";
            position: absolute !important;
            z-index: 3 !important;
            left: 16px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            pointer-events: none !important;
            font-size: 1rem !important;
            line-height: 1 !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"] :is(p, span, input) {
            color: var(--pp-dd-muted) !important;
            -webkit-text-fill-color: var(--pp-dd-muted) !important;
            font-size: .9rem !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"] input::placeholder {
            color: #8290a5 !important;
            -webkit-text-fill-color: #8290a5 !important;
            opacity: 1 !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"] svg {
            color: #d9e1ec !important;
            fill: #d9e1ec !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"] > div:hover {
            border-color: var(--pp-dd-border-hover) !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"]:focus-within > div {
            border-color: var(--pp-dd-border-focus) !important;
            box-shadow: 0 0 0 1px rgba(138,77,255,.72), 0 0 0 3px rgba(138,77,255,.09) !important;
        }

        .st-key-selected_categories_widget [data-baseweb="select"] > div > div:last-child {
            margin-left: auto !important;
            padding-right: 2px !important;
        }

        .st-key-selected_categories_widget [data-baseweb="tag"] {
            min-height: 30px !important;
            margin: 2px 5px 2px 0 !important;
            padding: 0 4px 0 8px !important;
            background: var(--pp-dd-chip-bg) !important;
            border: 1px solid var(--pp-dd-chip-border) !important;
            border-radius: 7px !important;
            color: #eaf0f8 !important;
        }

        .st-key-selected_categories_widget [data-baseweb="tag"] * {
            color: #eaf0f8 !important;
            -webkit-text-fill-color: #eaf0f8 !important;
        }

        /* SORT – geschlossen */
        .st-key-sort_mode [data-baseweb="select"] {
            position: relative !important;
            min-height: 42px !important;
            color-scheme: dark !important;
        }

        /* NEU: tatsächlichen Wrapper um das Combobox-Input färben */
        .st-key-sort_mode div:has(> input[role="combobox"]),
        .st-key-sort_mode div:has(> div > input[role="combobox"]) {
            background: #081522 !important;
            background-color: #081522 !important;
            background-image: none !important;
        }


        /* deine bestehenden Regeln danach */
        .st-key-sort_mode [data-baseweb="select"] > div {
            min-height: 42px !important;
            padding: 4px 38px 4px 12px !important;
            border: 1px solid var(--pp-dd-border) !important;
            border-radius: 8px !important;
        }

        .st-key-sort_mode [data-baseweb="select"] :is(p, span, input) {
            color: var(--pp-dd-text) !important;
            -webkit-text-fill-color: var(--pp-dd-text) !important;
            font-size: .875rem !important;
        }

        .st-key-sort_mode [data-baseweb="select"] > div,
        .st-key-sort_mode [data-baseweb="select"] > div > div,
        .st-key-sort_mode [data-baseweb="select"] [role="combobox"] {
            min-height: 42px !important;
            background: #081522 !important;
            background-color: #081522 !important;
            background-image: none !important;
            border-color: var(--pp-dd-border) !important;
            color: var(--pp-dd-text) !important;
            -webkit-text-fill-color: var(--pp-dd-text) !important;
        }

        /* Innere Text-/Icon-Ebenen transparent halten, damit kein graues BaseWeb-Layer sichtbar bleibt. */
        .st-key-sort_mode [data-baseweb="select"] > div > div * {
            background-color: transparent !important;
            background-image: none !important;
        }

        .st-key-sort_mode [data-baseweb="select"] > div {
            padding: 4px 38px 4px 12px !important;
            border: 1px solid var(--pp-dd-border) !important;
            border-radius: 8px !important;
        }

        .st-key-sort_mode [data-baseweb="select"]::before {
            content: none !important;
            display: none !important;
        }

        .st-key-sort_mode [data-baseweb="select"] :is(p, span, input) {
            color: var(--pp-dd-text) !important;
            -webkit-text-fill-color: var(--pp-dd-text) !important;
            font-size: .875rem !important;
        }

        .st-key-sort_mode [data-baseweb="select"] svg {
            color: #d9e1ec !important;
            fill: #d9e1ec !important;
        }

        .st-key-sort_mode [data-baseweb="select"] > div:hover {
            border-color: var(--pp-dd-border-hover) !important;
        }

        .st-key-sort_mode [data-baseweb="select"]:focus-within > div {
            border-color: var(--pp-dd-border-focus) !important;
            box-shadow: 0 0 0 1px rgba(138,77,255,.72), 0 0 0 3px rgba(138,77,255,.09) !important;
        }

        /* Geöffnete Menüs – Navy-Hintergrund auf ALLEN BaseWeb-Flächen.
           Wichtig: Option-Inhalte werden weiter unten wieder transparent gesetzt. */
        body [data-baseweb="popover"],
        body [data-baseweb="popover"] > div,
        body [data-baseweb="popover"] > div > div,
        body [data-baseweb="popover"] [data-baseweb="menu"],
        body [data-baseweb="popover"] [role="listbox"],
        body [data-baseweb="popover"] [role="listbox"] > div,
        body [data-baseweb="popover"] [role="listbox"] > div > div,
        body [data-baseweb="menu"],
        body [data-baseweb="menu"] > div,
        body [data-baseweb="menu"] > div > div,
        body [role="listbox"],
        body [role="listbox"] > div,
        body [role="listbox"] > div > div {
            background-color: #081522 !important; /*geöffnetes kleines dropdown farbe*/
            background-image: none !important;
            color: var(--pp-dd-text) !important;
            color-scheme: dark !important;
        }

        /* BaseWeb legt je nach Streamlit-Version zusätzliche Wrapper tiefer im Portal an.
           Diese bekommen ebenfalls Navy; die Optionszeilen selbst bleiben separat steuerbar. */
        body [data-baseweb="popover"] [role="listbox"] div,
        body [data-baseweb="menu"] [role="listbox"] div {
            background-color: #081522 !important;
            background-image: none !important;
        }

        body :is([data-baseweb="menu"], [role="listbox"]) {
            padding: 4px !important;
            border: 1px solid #2d4057 !important;
            border-radius: 8px !important;
            box-shadow: 0 18px 40px rgba(0,0,0,.42) !important;
            overflow: auto !important;
        }

        body :is([data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"]) input {
            min-height: 38px !important;
            padding: 0 10px !important;
            color: #eef3fb !important;
            -webkit-text-fill-color: #eef3fb !important;
            background: #0b1a2a !important;
            border: 1px solid #2e425b !important;
            border-radius: 8px !important;
            outline: none !important;
            box-shadow: none !important;
        }

        body [role="option"] {
            color: #e8edf5 !important;
            -webkit-text-fill-color: #e8edf5 !important;
            background: transparent !important;
            background-color: transparent !important;
            background-image: none !important;
            border-radius: 7px !important;
        }

        body [role="option"] *,
        body [role="option"] div,
        body [role="option"] span {
            color: inherit !important;
            -webkit-text-fill-color: inherit !important;
            background: transparent !important;
            background-color: transparent !important;
            background-image: none !important;
        }

        body [role="option"]:hover,
        body [role="option"][data-highlighted="true"] {
            background: var(--pp-dd-bg-hover) !important;
            background-color: var(--pp-dd-bg-hover) !important;
        }

        body [role="option"][aria-selected="true"] {
            background: linear-gradient(90deg, rgba(100,72,190,.27), rgba(49,46,99,.42)) !important;
            background-color: #202047 !important;
            color: #ffffff !important;
        }

        body [role="option"]::before,
        body [role="option"]::after {
            content: none !important;
        }

        body :is([data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"]) ::-webkit-scrollbar {
            width: 7px !important;
            height: 7px !important;
        }

        body :is([data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"]) ::-webkit-scrollbar-thumb {
            background: #40536c !important;
            border-radius: 999px !important;
        }


        /* ---------- Section Title ---------- */
        .pp-section-title {
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 4px;
            letter-spacing: -0.3px;
        }

        .pp-section-sub {
            font-size: 18px;
            color: var(--pp-muted);
            margin-bottom: 32px;
        }

        .pp-form-wrapper {
            padding-left: 6px;
            padding-top: 10px;
        }

        /* Dropdown styling is defined globally above. */

        /* Clear all ganz rechts ausrichten */
        .st-key-clear_cuisine_btn {
            display: flex !important;
            justify-content: flex-end !important;
        }

        .st-key-clear_cuisine_btn div[data-testid="stButton"] {
            width: auto !important;
            margin-left: auto !important;
        }

        .st-key-clear_cuisine_btn button {
            width: auto !important;
        }

        /* Food-Multiselect: rechte Icons an den rechten Rand */

        .st-key-selected_categories_widget
        [data-baseweb="select"] > div > div:last-child {
            margin-left: auto !important;
            padding-right: 4px !important;
        }

        /* Food / Streamlit Virtual Dropdown – eigentliche große Menüfläche */
        ul[data-testid="stSelectboxVirtualDropdown"],
        ul[data-testid="stSelectboxVirtualDropdown"] > div,
        ul[data-testid="stSelectboxVirtualDropdown"] > div > div {
            background: #081522 !important;
            background-color: #081522 !important;
            background-image: none !important;
        }


</style>
        """
    )


def render_header(active_step=1):
    """Rendert den gemeinsamen Hero-Header inklusive Logo, Bild und 2-Step-Navigation.
    
        ``active_step`` bestimmt, ob die Preferences-Seite (1) oder Results-Seite (2)
        visuell als aktueller Schritt markiert wird.
        
    """
    photo_style = (
        f"background-image:url('{HERO_URL}');"
        if HERO_URL
        else "background:linear-gradient(120deg,#111f31,#07111d);"
    )

    logo_html = (
        f'<img src="{LOGO_URL}" class="pp-logo" alt="PlatePilot Logo">'
        if LOGO_URL
        else '<div class="pp-logo" style="display:grid;place-items:center;font-size:3.2rem;">🍽️</div>'
    )

    steps = [
        ("Preferences", "Cuisine & preferences"),
        ("Results", "Top restaurants"),
    ]
    steps_html = []

    for i, (title, subtitle) in enumerate(steps, start=1):
        if i < active_step:
            cls, txt = "pp-step done", "✓"
        elif i == active_step:
            cls, txt = "pp-step active", str(i)
        else:
            cls, txt = "pp-step", str(i)

        steps_html.append(
            f'<div class="{cls}">'
            f'<div class="pp-step-circle">{txt}</div>'
            f'<div class="pp-step-text">'
            f'<div class="pp-step-label">{i} {html.escape(title)}</div>'
            f'<div class="pp-step-subtitle">{html.escape(subtitle)}</div>'
            f'</div>'
            f'</div>'
        )

    progress_html = '<div class="pp-progress">' + "".join(steps_html) + "</div>"

    st.html(
        f"""
        <section class="pp-header">
            <div class="pp-header-photo" style="{photo_style}"></div>
            <div class="pp-header-overlay"></div>

            <div class="pp-header-content">
                <div class="pp-logo-shell">
                    {logo_html}
                </div>
                <div class="pp-brand">
                    <h1>PlatePilot<br><span>Navigator</span></h1>
                    <p>Your guide to delicious decisions.</p>
                </div>
            </div>

            {progress_html}
        </section>
        """
    )

def _display_category(label):
    """Entfernt bei Bedarf ein vorangestelltes UI-Symbol aus einem Kategorienamen.
    """
    if not label:
        return label
    parts = str(label).split(" ", 1)
    if len(parts) == 2 and not parts[0][0].isalnum():
        return parts[1]
    return str(label)


def _restaurant_features(r):
    """Erzeugt eine lesbare Liste der verfügbaren Eigenschaften eines Restaurants.
    """
    attr = normalize_attributes(r.get("attributes", {}))
    items = []
    checks = [
        ("BusinessAcceptsCreditCards", "Credit Card"),
        ("RestaurantsTakeOut", "Takeout"),
        ("WiFi", "Wi-Fi"),
        ("WheelchairAccessible", "Wheelchair"),
        ("HappyHour", "Happy Hour"),
        ("OutdoorSeating", "Outdoor"),
        ("HasTV", "TV"),
        ("RestaurantsReservations", "Reservations"),
        ("DogsAllowed", "Dogs Allowed"),
        ("Alcohol", "Alcohol"),
        ("GoodForKids", "Good for Kids"),
        ("GoodForGroups", "Good for Groups"),
        ("BusinessParking", "Parking"),
        ("BikeParking", "Bike Parking"),
    ]
    for key, label in checks:
        if truthy_attr(attr.get(key)):
            items.append(label)
    if attr.get("NoiseLevel") == "quiet":
        items.append("Quiet")
    return items


def _run_recommendation(selected_raw, selected_kitchen, selected_price, distance,
                        alpha, w_cat, w_attr, w_price, w_dist):
    """Übersetzt die UI-Auswahl in Modellparameter und startet das Ranking.
    
        Die Funktion speichert zunächst Filter und Einstellungen im Session State,
        erzeugt anschließend User-Vektoren für Kategorien und Attribute und ruft
        ``get_recommendations(...)`` aus ``recommendation.py`` auf.
    
        Danach werden die Ergebnisse für die Results-Seite vorbereitet und ein Streamlit-
        Rerun ausgelöst.
        
    """
    st.session_state["filter_values"] = {
        "selected_raw": selected_raw,
        "selected_kitchen": selected_kitchen,
        "selected_price": selected_price,
        "distance": distance,
        "selected_extras": list(st.session_state["selected_extras"]),
        "alpha": alpha,
        "w_cat": w_cat,
        "w_attr": w_attr,
        "w_price": w_price,
        "w_dist": w_dist,
    }

    st.session_state["filters"] = {
        "kitchen": selected_kitchen,
        "price_range": selected_price,
        "distance": distance,
        "extras": list(st.session_state["selected_extras"]),
        "coords": st.session_state["coords"].copy(),
        "alpha": alpha,
        "w_cat": w_cat,
        "w_attr": w_attr,
        "w_price": w_price,
        "w_dist": w_dist,
    }

    price_to_int = {"﹩": 1, "﹩﹩": 2, "﹩﹩﹩": 3, "﹩﹩﹩﹩": 4}
    u_price = price_to_int[selected_price]

    selected_category_names = [
        KITCHEN_MAP.get(_display_category(k), _display_category(k))
        for k in selected_kitchen
    ]

    u_cat = [1 if col in selected_category_names else 0 for col in category_columns]

    selected_attr_names = [
        normalize_extra_name(x)
        for x in st.session_state["selected_extras"]
    ]

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

    selected_attr_columns = [
        extra_to_column[x]
        for x in selected_attr_names
        if x in extra_to_column
    ]

    u_attr = [1 if col in selected_attr_columns else 0 for col in attr_columns]

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

    if recommended_df.empty:
        st.session_state["results"] = []
    else:
        recommended_df["distance_km"] = recommended_df["calc_distance"].round(2)
        recommended_df["final_score"] = recommended_df["SCORE"].round(3)
        st.session_state["results"] = recommended_df.to_dict(orient="records")

    st.session_state["results_page_index"] = 0
    st.session_state["show_results_map"] = False
    st.session_state.page = "results"
    st.rerun()


# =========================================================
# Seite 1: Filter / Preferences
# =========================================================
FOOD_SECTION_HEADERS = {
    "CUISINE--------------------------------",
    "DISH----------------------------------",
    "VENUE---------------------------------",
}


def prevent_food_header_selection():
    """Überschriften im Food-Dropdown dürfen nicht ausgewählt werden."""
    st.session_state["selected_categories_widget"] = [
        item
        for item in st.session_state.get("selected_categories_widget", [])
        if item not in FOOD_SECTION_HEADERS
    ]

def show_form():
    """Rendert Seite 1: Standort- und Präferenzformular.
    
        Hier wählt der Benutzer Küche/Kategorien, Preis, maximale Entfernung und optionale
        Restaurantmerkmale. Beim Absenden wird ``_run_recommendation(...)`` aufgerufen.
        
    """
    inject_platepilot_css()
    render_header(active_step=1)
    

    lat = st.session_state["coords"]["lat"]
    lon = st.session_state["coords"]["lon"]
    stadt, strasse = reverse_geocode_cached(lat, lon)
    stadt = stadt or "Philadelphia"
    strasse = strasse or "North 15th Street"

    with st.container(key="user_card"):
        c1, c2, c3, c4 = st.columns([0.75, 4.6, 2.4, 1.58], vertical_alignment="center")

        with c1:
            st.html('<div class="pp-round-icon">👋</div>')

        with c2:
            st.html(
                """
                <h2 class="pp-user-title">Hi Mike 👋</h2>
                <p class="pp-user-sub">Ready to find your next favorite meal?</p>
                """
            )

        with c3:
            st.html(
                f'<div class="pp-location">📍 &nbsp;{html.escape(stadt)},<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{html.escape(strasse)}</div>'
            )

        with c4:
            if st.button("✎ Edit", key="edit_location", use_container_width=True):
                st.session_state["show_map"] = not st.session_state["show_map"]
                st.rerun()

    if st.session_state["show_map"]:
        with st.container():
            st.markdown("#### 📍 Edit Location")
            st.caption("Click anywhere on the map to choose your location.")
            m = folium.Map(location=[lat, lon], zoom_start=12)
            folium.Marker(
                [lat, lon],
                tooltip="Your chosen location",
                icon=folium.Icon(color="red", icon="info-sign"),
            ).add_to(m)
            map_data = st_folium(m, height=360, use_container_width=True)

            if map_data and map_data.get("last_clicked"):
                st.session_state["new_coords"] = {
                    "lat": map_data["last_clicked"]["lat"],
                    "lon": map_data["last_clicked"]["lng"],
                }

            new_lat = st.session_state["new_coords"]["lat"]
            new_lon = st.session_state["new_coords"]["lon"]
            new_city, new_street = reverse_geocode_cached(new_lat, new_lon)
            st.caption(f"Selected: {new_city or 'Philadelphia'}, {new_street or 'Unknown Street'}")

            save_col, cancel_col, _ = st.columns([1.2, 1.2, 5])
            with save_col:
                if st.button("💾 Save location", type="primary", use_container_width=True):
                    st.session_state["coords"] = st.session_state["new_coords"].copy()
                    st.session_state["show_map"] = False
                    st.rerun()
            with cancel_col:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["new_coords"] = st.session_state["coords"].copy()
                    st.session_state["show_map"] = False
                    st.rerun()

    # Intro und alle Filter befinden sich jetzt in EINER gemeinsamen Card.
    with st.container(key="main_form_card"):

        # -------------------------------------------------
        # Intro / Reset
        # -------------------------------------------------
        q1, q2, q3 = st.columns([0.75, 6.1, 1.4], vertical_alignment="center")

        with q1:
            st.html('<div class="pp-round-icon">✦</div>')

        with q2:
            st.html(
                """
                <h2 class="pp-user-title">What would you like to eat today?</h2>
                <p class="pp-user-sub">Let's find something amazing for you.</p>
                """
            )

        with q3:
            st.button(
                "⟳ Reset",
                key="reset",
                on_click=reset_filter_state,
                use_container_width=True,
            )

        # optische Trennung innerhalb derselben Card
        st.html('<div class="pp-form-divider"></div>')

        # -------------------------------------------------
        # 1. Cuisine / Food
        # -------------------------------------------------
        # Flat options: no fake selectable section headers inside st.multiselect.
        # This keeps the opened menu visually clean, like the reference dropdown.
        grouped_list = [
           "CUISINE--------------------------------", "🥨 European", "🍜 Asian", "🥡 Chinese", "🍣 Japanese",
            "🌮 Mexican", "🥙 Latin American", "🧆 Middle Eastern",
            "🌍 African", "🍝 Italian", "🥗 Mediterranean",
            "🕌 South Asian", "🍗 American Traditional",
            "🌱 Vegetarian / Vegan", "🍖 American New",
            "DISH----------------------------------",
            "🍔 Burgers", "🍟 Fast Food", "🍕 Pizza", "🥗 Healthy Options",
            "🍗 Chicken", "🐟 Seafood", "🥪 Sandwiches", "🍜 Noodles",
            "🍲 Soup", "🍰 Desserts", "🥐 Bakeries", "🧃 Juice & Smoothies",
            "🥩 Steak & Barbeque", 
            "VENUE---------------------------------","🍸 Bars & Nightlife", "☕ Coffee & Tea",
            "🍳 Breakfast & Brunch", "🍽️ Casual & Quick",
        ]

        st.html('<div class="pp-filter-head" style="margin-top:.15rem;">1. Cuisine / Food</div>')
        #st.html('<div class="pp-filter-caption">🍴 Select one or more categories:</div>')

        #---DROPDOWN AUFBAU-----#

        selected_raw = st.multiselect(
            "Cuisine / Food",
            grouped_list,
            key="selected_categories_widget",
            placeholder="Choose cuisine categories...",
            label_visibility="collapsed",
            on_change=prevent_food_header_selection,
        )

        selected_raw = [
            item for item in selected_raw
            if item not in FOOD_SECTION_HEADERS
        ]

        selected_kitchen = list(selected_raw)

        # Kleine Statuszeile unter dem Feld – analog zum Design-Mockup.
        selected_count = len(selected_raw)

        cuisine_status_col, cuisine_clear_col = st.columns([16, 1], vertical_alignment="center")
        with cuisine_status_col:
            if selected_count:
                st.html(
                    f'<div class="pp-cuisine-count">'
                    f'{selected_count} selected'
                    f'</div>'
                )
            else:
                st.html('<div class="pp-cuisine-count">Select one or more categories</div>')

        with cuisine_clear_col:
            if selected_count:
                st.button(
                    "Clear all",
                    key="clear_cuisine",
                    on_click=clear_cuisine_selection,
                    use_container_width=False,
                )

        selected_kitchen = list(selected_raw)

        st.html('<div class="pp-form-divider"></div>')

        # -------------------------------------------------
        # 2. Price + 3. Distance
        # -------------------------------------------------
        price_col, dist_col = st.columns(2, gap="large")

        with price_col:
            st.html('<div class="pp-filter-head">2. Price</div>')

            price_options = ["﹩", "﹩﹩", "﹩﹩﹩", "﹩﹩﹩﹩"]

            selected_price = st.select_slider(
                "Select preferred price:",
                options=price_options,
                key="price_widget",
            )

            st.caption(f"Selected price: {selected_price}")
          
        with dist_col:
            st.html('<div class="pp-filter-head">3. Distance</div>')

            distance = st.slider(
                "Select maximum distance:",
                min_value=1,
                max_value=50,
                step=1,
                key="dist_slider",
            )

            st.caption(f"Selected distance: up to {distance} km")


        # -------------------------------------------------
        # 4. Additional Options
        # -------------------------------------------------

        st.html('<div class="pp-form-divider"></div>')

        st.html('<div class="pp-filter-head">4. Additional Options</div>')

        extras_list = [
            "Wi-Fi", "Outdoor", "Credit Card", "Reservations", "Takeout",
            "Parking", "Happy Hour", "Dogs Allowed", "TV", "Wheelchair",
            "Alcohol", "Quiet", "Bike Parking", "Good for Kids", "Good for Groups",
        ]

        for start in range(0, len(extras_list), 5):
            row = extras_list[start:start + 5]
            cols = st.columns(len(row))

            for col, extra in zip(cols, row):
                with col:
                    is_selected = extra in st.session_state["selected_extras"]
                    button_type = "primary" if is_selected else "secondary"
                    key_safe = re.sub(r"[^a-zA-Z0-9_]+", "_", extra.lower())

                    if st.button(
                        f"{'✓ ' if is_selected else ''}{extra}",
                        key=f"chip_{key_safe}",
                        type=button_type,
                        use_container_width=True,
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

        if st.session_state["selected_extras"]:
            st.markdown(
                "**Your preferences:** "
                + ", ".join(st.session_state["selected_extras"])
            )

        # -------------------------------------------------
        # Advanced settings
        # -------------------------------------------------
        st.html('<div class="pp-form-divider"></div>')

        st.html(
            '<div class="pp-advanced-info">'
            '<span class="pp-info-icon">i</span>'
            '<span>Fine-tune how cuisine, extras, price and distance '
            'influence your recommendations.</span>'
            '</div>'
        )


        with st.expander(
            "⚙️ Advanced recommendation settings",
            expanded=False,
        ):
            st.caption("Balance global popularity and personal fit.")

            alpha = st.slider(
                "Global ↔ Personal Fit",
                0.0,
                1.0,
                0.6,
                key="alpha_widget",
            )

            w_cat = st.slider(
                "Cuisine Flexible ↔ Strong Cuisine Match",
                0.0,
                10.0,
                4.0,
                key="w_cat_widget",
            )

            w_attr = st.slider(
                "Extras Optional ↔ Must-Have Extras",
                0.0,
                10.0,
                3.0,
                key="w_attr_widget",
            )

            w_price = st.slider(
                "Price Flexible ↔ Strict Price Match",
                0.0,
                10.0,
                2.0,
                key="w_price_widget",
            )

            w_dist = st.slider(
                "Distance Flexible ↔ Nearby Restaurants",
                0.0,
                10.0,
                1.0,
                key="w_dist_widget",
            )

        # -------------------------------------------------
        # Tip + Navigation
        # -------------------------------------------------
        st.html(
            '<div class="pp-tip">✨ <strong>Tip:</strong> '
            'Combine cuisine, distance and extras to get more relevant '
            'restaurant recommendations.</div>'
        )

        left, _ = st.columns([2.0, 5])

        with left:
            with st.container(key="find_restaurants_cta"):
                if st.button(
                    "Find restaurants →",
                    type="primary",
                    use_container_width=True,
                ):
                    _run_recommendation(
                        selected_raw,
                        selected_kitchen,
                        selected_price,
                        distance,
                        alpha,
                        w_cat,
                        w_attr,
                        w_price,
                        w_dist,
                    )



# =========================================================
# Seite 2: Restaurant-Auswahl / Recommendations
# =========================================================

def show_results():
    """Rendert Seite 2: gerankte Restaurantempfehlungen.
    
        Die Seite zeigt die gewählten Filter, ermöglicht Sortierung und Pagination und
        stellt pro Restaurant Match-Score, Bewertung, Distanz, Preis, Eigenschaften,
        Wegbeschreibung und Detailinformationen dar.
        
    """
    inject_platepilot_css()
    render_header(active_step=2)

    results = st.session_state.get("results", [])
    filters = st.session_state.get("filters", {})

    if "results_page_index" not in st.session_state:
        st.session_state["results_page_index"] = 0
    if "show_results_map" not in st.session_state:
        st.session_state["show_results_map"] = False

    if not results:
        st.warning("No restaurants match your current preferences. Please adjust your filters.")
        if st.button(
            "✎ Edit preferences",
            type="primary",
            use_container_width=True
        ):
            st.session_state.page = "form"
            st.rerun()

    with st.container(key="results_shell"):
        side_col, main_col = st.columns([1.05, 3.0], gap="medium")

        with side_col:
            with st.container(key="results_sidebar"):
                st.html(
                    """
                    <div class="pp-side-head">
                        <h3>Your Selections</h3>
                        <p>Refine your results</p>
                    </div>
                    """
                )

                kitchen_values = filters.get("kitchen", [])
                kitchen_text = ", ".join(_display_category(x) for x in kitchen_values) or "Any cuisine"
                price_text = filters.get("price_range", "﹩﹩")
                distance_text = f"Up to {filters.get('distance', 10)} km"
                extras = filters.get("extras", [])

                st.html(
                    f"""
                    <div class="pp-summary-block">
                        <div class="pp-summary-label">🍴 Cuisine / Food</div>
                        <div class="pp-summary-value">{html.escape(kitchen_text)}</div>
                    </div>
                    <div class="pp-summary-block">
                        <div class="pp-summary-label">💲 Price</div>
                        <div class="pp-summary-value">{html.escape(str(price_text))}</div>
                    </div>
                    <div class="pp-summary-block">
                        <div class="pp-summary-label">📍 Distance</div>
                        <div class="pp-summary-value">{html.escape(distance_text)}</div>
                    </div>
                    <div class="pp-summary-block">
                        <div class="pp-summary-label">☆ Additional Options</div>
                        <div class="pp-summary-value">
                            {"<br>".join("✓ " + html.escape(x) for x in extras) if extras else "No additional options"}
                        </div>
                    </div>
                    <div class="pp-count">
                        <strong>{len(results)}</strong>
                        <span>matching restaurants</span>
                    </div>
                    """
                )

                if st.button(
                    "✎ Edit preferences",
                    type="primary",
                    use_container_width=True
                ):
                    st.session_state.page = "form"
                    st.rerun()

                if st.button("⟳ Reset all", use_container_width=True):
                    reset_filter_state()
                    st.session_state.page = "form"
                    st.rerun()

                st.html("<div style='height:.5rem'></div>")

               # if st.button("← Back", use_container_width=True):
                  #  st.session_state.page = "form"
                   # st.rerun()

        with main_col:
            with st.container(key="results_main"):
                st.html(
                    """
                    <div class="pp-results-head">
                        <h2>🍴 Top Restaurant Recommendations</h2>
                        <p>Based on your preferences</p>
                    </div>
                    """
                )

                toolbar_left, toolbar_mid = st.columns([5.5, 1.8], vertical_alignment="bottom")
                with toolbar_mid:
                    sort_mode = st.selectbox(
                        "Sort by",
                        ["Best Match", "Rating", "Distance", "Most Reviewed"],
                        label_visibility="collapsed",
                        key="sort_mode",
                    )


                sorted_results = list(results)
                if sort_mode == "Rating":
                    sorted_results.sort(key=lambda r: float(r.get("rating", r.get("stars_real", 0)) or 0), reverse=True)
                elif sort_mode == "Distance":
                    sorted_results.sort(key=lambda r: float(r.get("distance_km", 9999) or 9999))
                elif sort_mode == "Most Reviewed":
                    sorted_results.sort(key=lambda r: int(r.get("review_count", 0) or 0), reverse=True)
                else:
                    sorted_results.sort(key=lambda r: float(r.get("final_score", 0) or 0), reverse=True)

                page_size = 6
                total_pages = max(1, (len(sorted_results) + page_size - 1) // page_size)
                page_index = min(st.session_state["results_page_index"], total_pages - 1)
                start = page_index * page_size
                visible_results = sorted_results[start:start + page_size]

                for rank, r in enumerate(visible_results, start=start + 1):
                    stars = r.get("stars_real")
                    if stars is None or pd.isna(stars):
                        stars = r.get("rating", 0)
                    try:
                        stars = float(stars or 0)
                    except Exception:
                        stars = 0.0

                    try:
                        distance = float(r.get("distance_km", 0) or 0)
                    except Exception:
                        distance = 0.0

                    try:
                        raw_score = float(r.get("final_score", 0) or 0)
                    except Exception:
                        raw_score = 0.0

                    # SCORE liegt normalerweise in 0..1.
                    match_pct = max(0, min(100, int(round(raw_score * 100))))
                    features = _restaurant_features(r)[:5]
                    categories = r.get("categories", []) or []
                    category_text = " · ".join(str(c).replace("_", " ") for c in categories[:3])
                    price = r.get("price", "﹩﹩")
                    reviews = int(r.get("review_count", 0) or 0)

                    chips = "".join(
                        f'<span class="pp-mini-chip">{html.escape(x)}</span>'
                        for x in features
                    )

                    lat = r.get("latitude")
                    lon = r.get("longitude")

                    if pd.notna(lat) and pd.notna(lon):
                        maps_url = (
                            "https://www.google.com/maps/search/"
                            f"?api=1&query={float(lat)},{float(lon)}"
                        )
                    else:
                        address = r.get("address", "")
                        maps_query = quote_plus(
                            address if address else str(r.get("name", ""))
                        )
                        maps_url = (
                            "https://www.google.com/maps/search/"
                            f"?api=1&query={maps_query}"
                        )

                    with st.container(key=f"restaurant_card_{rank}"):

                        st.html(
                            f"""
                            <div class="pp-result-content">
                                <div style="display:grid;grid-template-columns:42px 1fr 170px;gap:1rem;align-items:start;">
                                    <div style="
                                        width:34px;height:34px;display:grid;place-items:center;
                                        border:1px solid #7055ff;border-radius:8px;
                                        background:#2b1c66;color:white;font-weight:800;
                                    ">{rank}</div>

                                    <div>
                                        <div class="pp-result-name">
                                            {html.escape(str(r.get("name", "Unknown Restaurant")))}
                                        </div>

                                        <a class="pp-directions-link"
                                        href="{html.escape(maps_url)}"
                                        target="_blank">
                                            📍 Directions
                                        </a>

                                        <div class="pp-result-meta">
                                            {html.escape(category_text or "Restaurant")}
                                        </div>

                                        <div class="pp-result-meta">
                                            ⭐ {stars:.1f} ({reviews:,}) &nbsp; • &nbsp;
                                            {html.escape(str(price))} &nbsp; • &nbsp;
                                            {distance:.1f} km
                                        </div>

                                        <div class="pp-chip-row">{chips}</div>
                                    </div>

                                    <div>
                                        <div class="pp-score">{match_pct}% Match</div>
                                        <div class="pp-progress-bar">
                                            <div class="pp-progress-fill" style="width:{match_pct}%"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """
                        )

                        # Directions direkt unter den Restaurant-Infos
                        #lat = r.get("latitude")
                        #lon = r.get("longitude")

                        if pd.notna(lat) and pd.notna(lon):
                            maps_url = (
                                "https://www.google.com/maps/search/"
                                f"?api=1&query={float(lat)},{float(lon)}"
                            )
                        else:
                            address = r.get("address", "")
                            maps_query = quote_plus(
                                address if address else str(r.get("name", ""))
                            )
                            maps_url = (
                                "https://www.google.com/maps/search/"
                                f"?api=1&query={maps_query}"
                            )

                       

                        with st.expander("View details"):
                            st.markdown(f"**Rating:** ⭐ {stars:.2f} ({reviews:,} reviews)")
                            st.markdown(f"**Distance:** {distance:.2f} km")
                            st.markdown(f"**Price:** {price}")

                            address = r.get("address", "")
                            st.markdown(f"**Address:** {address or 'No address available'}")

                            if categories:
                                st.markdown("**Categories:** " + ", ".join(map(str, categories)))

                            hours_data = normalize_attributes(r.get("hours", {}))
                            if hours_data:
                                st.markdown("**Opening Hours**")
                                day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                                lines = []
                                for day in day_order:
                                    hours = hours_data.get(day)
                                    if hours and hours not in {"None", "0:0-0:0", "0:00-0:00"}:
                                        lines.append(f"{day[:3]}: {format_opening_hours(hours)}")
                                st.write(" | ".join(lines) if lines else "No opening hours available.")

                            feature_list = _restaurant_features(r)
                            if feature_list:
                                st.markdown("**Restaurant Preferences:** " + ", ".join(feature_list))

                nav_left, nav_mid, nav_right = st.columns([1, 3, 1])
                with nav_left:
                    if st.button("← Previous", disabled=page_index <= 0, use_container_width=True):
                        st.session_state["results_page_index"] = max(0, page_index - 1)
                        st.rerun()
                with nav_mid:
                    st.html(
                        f"<div style='text-align:center;color:#aeb8c8;padding-top:.7rem;'>Page {page_index + 1} of {total_pages}</div>"
                    )
                with nav_right:
                    if st.button("Next →", disabled=page_index >= total_pages - 1, type="primary", use_container_width=True):
                        st.session_state["results_page_index"] = min(total_pages - 1, page_index + 1)
                        st.rerun()


# =========================================================
# Routing
# =========================================================

if st.session_state.page == "form":
    show_form()
else:
    show_results()
