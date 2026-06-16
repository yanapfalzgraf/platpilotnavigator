import streamlit as st

# Sidebar ausblenden
hide_sidebar = """
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="stSidebarNav"] {
            display: none;
        }
        /* Hauptbereich auf volle Breite ziehen */
        .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
        }
    </style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)
def filter_restaurants(restaurants, filters):
    # Fake-Filter: gibt einfach alle Restaurants zurück
    return restaurants

#UI Hauptteil 2 Seite
#st.markdown(hide_sidebar, unsafe_allow_html=True)

#breadcrumb
st.markdown(
    "<a href='/' style='text-decoration:none; font-weight:bold;'>Startseite</a>  >  Ergebnisse",
    unsafe_allow_html=True
)

#inhalt
st.title("🍽️ Deine Restaurant-Ergebnisse")
st.markdown("---")

# Prüfen, ob Ergebnisse vorhanden sind
if "results" not in st.session_state:
    st.warning("Bitte zuerst eine Suche auf der Hauptseite durchführen.")
    st.stop()

results = st.session_state["results"]

# Falls keine Ergebnisse
if not results:
    st.error("Keine Restaurants gefunden. Bitte passe deine Filter an.")
    st.stop()

# Ergebnisse anzeigen
st.markdown(f"### {len(results)} Restaurants gefunden")

for r in results:
    header = f"{r['name']} — ⭐ {r['rating']} | {r['price']} | {r['distance_km']} km" #schleife über alle ergebnisse

    with st.expander(header): #accordion erstellen
#details
        # Kategorien
        st.markdown(f"**Kategorien:** {', '.join(r['categories'])}")

        # Bewertung
        st.markdown(f"**Bewertung:** ⭐ {r['rating']} ({r['review_count']} Reviews)")

        # Öffnungszeiten
        st.subheader("Öffnungszeiten")
        for day, hours in r["hours"].items():
            st.write(f"{day}: {hours}")

        # Extras
        st.subheader("Extras")
        extras_list = []
        attr = r["attributes"]

#extras aus attributen ableiten
        if attr.get("WiFi") and attr["WiFi"] != "no": #übersetzung von den rohen Attributen in lesbare Extras.
            extras_list.append("WLAN")
        if attr.get("OutdoorSeating"):
            extras_list.append("Outdoor")
        if attr.get("BusinessAcceptsCreditCards"):
            extras_list.append("Kreditkarte")
        if attr.get("RestaurantsReservations"):
            extras_list.append("Reservierung")
        if attr.get("RestaurantsTakeOut"):
            extras_list.append("Takeout")
        if attr.get("Parking") and attr["Parking"] != "none":
            extras_list.append("Parken")

        st.write(", ".join(extras_list) if extras_list else "Keine Extras") # Wenn extras_list nicht leer ist → verbinde mit Komma: "WLAN, Outdoor, Parken"

        # Adresse
        st.subheader("Adresse")
        st.write(r["address"])

        # Google Maps Link
        maps_url = f"https://www.google.com/maps/search/?api=1&query={r['address']}"
        st.link_button("📍 Route öffnen", maps_url)
