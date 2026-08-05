from pathlib import Path
import html
import streamlit as st
import base64
import mimetypes

from chatbot import (
    contact_form_dialog,
    init_chat_state,
    render_floating_chat,
)

BASE_DIR = Path(__file__).parent
PORTRAIT_PATH = BASE_DIR / "assets" / "images" / "yp_image.png"
def get_image_data_url(relative_path: str) -> str:
    image_path = BASE_DIR / relative_path

    if not image_path.is_file():
        raise FileNotFoundError(f"Bild nicht gefunden: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path)

    if mime_type is None:
        mime_type = "application/octet-stream"

    encoded = base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"

def get_base64_image(path: Path) -> str:
    with path.open("rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


portrait_base64 = get_base64_image(PORTRAIT_PATH)

clock_icon = get_image_data_url("assets/icons/clock.svg")
workflow_icon = get_image_data_url("assets/icons/workflow.svg")
chart_icon = get_image_data_url("assets/icons/chart-column-big.svg")

users_icon = get_image_data_url("assets/icons/users.svg")
search_icon = get_image_data_url("assets/icons/search.svg")
lightbulb_icon = get_image_data_url("assets/icons/lightbulb.svg")
target_icon = get_image_data_url("assets/icons/crosshair.svg")
growth_icon = get_image_data_url("assets/icons/chart-column-decreasing.svg")
st.set_page_config(
    page_title="Yana Pfalzgraf | Data Analystin & UX",
    page_icon="YP",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_chat_state()


def open_contact_form() -> None:
    """Öffnet ausschließlich das Kontaktformular."""
    st.session_state["contact_form_open"] = True


st.html(BASE_DIR / "assets" / "style.css")
st.markdown(
    """
    <style>
    /* Dialog insgesamt breiter */
    div[data-testid="stDialog"] > div[role="dialog"] {
        width: min(1500px, 97vw) !important;
        max-width: 1500px !important;
        max-height: 94vh !important;
        overflow-y: auto !important;
        border-radius: 18px !important;
    }


    /* Hauptbild im Projekt-Dialog */
    .case-image-frame {
        width: 100%;
        max-width: none;
        margin: 0;
        padding: 0;
        overflow: hidden;
        border: 1px solid #dbe3df;
        border-radius: 16px;
        background: #f7f9f8;
    }

    .case-image-frame img {
        width: 100%;
        max-width: none;
        height: auto;
        display: block;
        object-fit: contain;
    }

    .case-counter {
        margin-top: 0.45rem;
        margin-bottom: 0.9rem;
        text-align: center;
        color: #64736e;
        font-size: 0.85rem;
    }

    /* Unterer Informationsbereich: exakt drei Spalten */
    .case-description-grid {
        display: grid;
        grid-template-columns: 1.15fr 1fr 1.15fr;
        gap: 3rem;
        align-items: start;

        margin-top: 1.5rem;
        padding: 1.7rem 0 1.8rem;
        border-top: 1px solid #dfe5e1;
    }

    .case-description-grid section {
        min-width: 0;
    }

    .case-description-grid h4 {
        margin: 0 0 0.85rem;
        color: #1f5a49;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.11em;
        text-transform: uppercase;
    }

    .case-description-grid p {
        margin: 0;
        color: #3e4d48;
        font-size: 0.91rem;
        line-height: 1.65;
    }

    /* Abstand zwischen Rolle und Tools */
    .case-tools-heading {
        margin-top: 1.45rem !important;
    }

    /* Tools nebeneinander */
    .case-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        align-items: center;
    }

    .case-chip {
        display: inline-flex;
        align-items: center;
        padding: 0.4rem 0.65rem;

        border: 1px solid #d6dfda;
        border-radius: 999px;
        background: #f5f7f6;

        color: #29483e;
        font-size: 0.78rem;
        white-space: nowrap;
    }

    /* Highlights */
    .case-highlights {
        display: grid;
        gap: 0.7rem;
        margin: 0;
        padding: 0;
        list-style: none;
    }

    .case-highlights li {
        display: flex;
        align-items: flex-start;
        gap: 0.55rem;

        color: #3e4d48;
        font-size: 0.9rem;
        line-height: 1.45;
    }

    .case-check {
        width: 1.15rem;
        height: 1.15rem;
        flex: 0 0 1.15rem;

        display: inline-flex;
        align-items: center;
        justify-content: center;

        margin-top: 0.05rem;
        border-radius: 50%;
        background: #1f5a49;
        color: white;

        font-size: 0.7rem;
        font-weight: 700;
    }

    /* Trennlinie vor der Projekt-Navigation */
    .case-project-footer-divider {
        margin: 0;
        padding-top: 1rem;
        border-top: 1px solid #dfe5e1;
    }

    /* Projektzähler in der Mitte */
    .case-project-counter {
        padding: 0.8rem 0;
        text-align: center;
        color: #43534d;
        font-size: 0.9rem;
        font-weight: 600;
    }

    /* Footer-Buttons */
    div[data-testid="stDialog"] button {
        min-height: 42px;
        border-radius: 8px;
    }

    /* Erst auf kleinen Displays untereinander */
    @media (max-width: 720px) {
        .case-description-grid {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }
    }

    /* Lokale Lucide-Icons */
    .expertise-icon img {
        width: 25px;
        height: 25px;
        display: block;
        object-fit: contain;
        filter: brightness(0) invert(1);
    }

    .process-icon img {
        width: 24px;
        height: 24px;
        display: block;
        object-fit: contain;
        opacity: 0.78;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

PROJECTS_UX = [
    {
        "title": "Murrelektronik",
        "subtitle": "UX/UI Design · Prototyping · Stakeholder Austausch",
        "image": "assets/images/murrelektronik.svg",
        "card_image": "assets/images/Murrelektronik.svg",
        "cover_image": "assets/images/Murrelektronik.svg",
        "description": "Entwicklung einer nutzerzentrierten UX für eine digitale Installationsplattform, die Mitarbeitende visuell und interaktiv durch komplexe Verdrahtungsprozesse begleitet.",
        "tags": ["UX Research", "UI Design", "Figma", "Prototyping"],

        "gallery": [
        "assets/images/Murrelektronik.svg",
        "assets/images/murrelektronik4.svg",
        "assets/images/murrelektronik5.svg",
        "assets/images/murrelektronik6.svg",
        ],
    },
    {
        "title": "OPTIMA",
        "subtitle": "UX/UI Design · Web & Software · Industrial IT",
        "image": "assets/images/optima.svg",
        "card_image": "assets/images/optima.svg",
        "cover_image": "assets/images/optima.svg",
        "description": "UX/UI Design verschiedener Anwendungen für industrielle Arbeitsabläufe – von der Konzeption bis zur Gestaltung intuitiver Benutzeroberflächen.",
        "tags": ["User Flows", "Sketch", "Adobe XD", "Design System"],

        "gallery": [
        "assets/images/optima.svg",
        "assets/images/optima2.svg",
        "assets/images/optima3.svg",
        "assets/images/optima4.svg",
        ],
    },
    {
        "title": "MeaPuna",
        "subtitle": "SAP UI5 Entwicklung · UX/UI Design · Prototyping",
        "image": "assets/images/meapuna.svg",
        "card_image": "assets/images/meapuna.svg",
        "cover_image": "assets/images/meapuna.svg",
        "description": "Verantwortung für UX/UI Design und Frontend-Entwicklung (SAPUI5) in zwei Softwareprojekten – von der ersten Idee bis zur produktiven Umsetzung.",
        "tags": ["SAP UI5 Programming","SAP Fiori Apps Reference Library", "Wireframes", "Usability"],

        "gallery": [
        "assets/images/meapuna.svg",
        "assets/images/meaouna.svg",
        "assets/images/meapuna2.svg",
        "assets/images/meapuna3.svg",
        ],
    },
    {
        "title": "Mercedes-Benz / CINTEO",
        "subtitle": "UX/UI Design · In-Car-System · Stakeholder Austausch",
        "image": "assets/images/mercedes.svg",
        "card_image": "assets/images/cinteo.svg",
        "cover_image": "assets/images/cinteo.svg",
        "description": "Interface-Konzept für ein digitales Produkterlebnis im automobilen Kontext.",
        "tags": ["Interaction Design", "Axure", "Automotive", "UI"],

        "gallery": [
        "assets/images/cinteo.svg",
        "assets/images/cinteo4.svg",
        "assets/images/cinteo2.svg",
        "assets/images/cinteo_suche_3.svg",
        ],
    },
]

PROJECTS_DATA = [
    {
        "title": "Projekt 01 · Autoscout 24",
        "subtitle": "Data Analytics · Power BI · DAX · Python",
        "image": "assets/images/data_prediction.svg",
        "card_image": "assets/images/dsi1.svg",
        "cover_image": "assets/images/dsi1.svg",
        "description": (
           "AutoScout24-Datensatz · Analyse des Gebrauchtwagenmarktes · Preisentwicklung nach Baujahr · Marken- und Modellvergleich · Auswertung von Laufleistung, Leistung und Kraftstoffarten · Interaktive Filter und KPIs · DAX Measures · Power Query · Star Schema · Dashboard zur datengetriebenen Fahrzeuganalyse."
        ),
        "tags": [
            "Power BI",
            "Data Analytics",
            "Dashboard Design",
            "DAX",
            "Python",
            "Power Query",
            "ML",
        ],
        "gallery": [
            "assets/images/dsi1.svg",
            "assets/images/dsi2.svg",
            "assets/images/dsi3.svg",
            "assets/images/dsi4.svg",
            "assets/images/dsi5.svg",
            "assets/images/dsi6.svg",
            "assets/images/dsi7.svg",
        ],
    },
    {
        "title": "Projekt 02 · PlatePilot Navigator App",
        "subtitle": "Empfehlungssystem · Scoring-Modell · Streamlit · Python",
        "image": "assets/images/data_forecasting.svg",
        "card_image": "assets/images/ppnavigator.svg",
        "cover_image": "assets/images/ppnavigator.svg",
        "description": "Restaurant-Empfehlungsplattform · Personalisierte Filter · Gewichtetes Empfehlungssystem · Kartenintegration · Interaktive Datenvisualisierung · Restaurantsuche · Standortbasierte Empfehlungen · Streamlit · Python · Benutzerfreundliche Navigation · Datenanalyse · API-Integration",
        "demo_url": "https://platpilotnavigatorapp.streamlit.app/",
        "tags": ["Python", "Streamlit", "Pandas", "Scikit-learn", "NumPy", "Folium", "GeoPy", "Parquet"],

        "gallery": [
        "assets/images/ppnavigator.svg",
        "assets/images/ppnavigator2.svg",
        ],
    },
    {
        "title": "Projekt 03 · Olympische Spiele",
        "subtitle": "Data Analytics · Power BI · DAX · Python",
        "image": "assets/images/data_insights.svg",
        "card_image": "assets/images/dsi.svg",
        "cover_image": "assets/images/dsi.svg",
        "description": (
    "Olympische Datenanalyse · Star Schema · Power BI · DAX Measures · Dimensionen & Faktentabelle · Länderdominanz · Frauen-/Männer-Teilnahme · Historische Entwicklungen · Sportartenwachstum · Participation Rate · Gender Gap · Female-to-Male Ratio · Trendanalysen"
),
        "tags": ["Power BI", "Data Visualization", "DAX", "Power Query"],

        "gallery": [
        "assets/images/dsi.svg",
        ],
    },
]

# Zusätzliche Daten für die Projekt-Detailansicht.
# Pro Projekt kannst du später mehrere Bilder in "gallery" ergänzen.
ALL_PROJECTS = PROJECTS_UX + PROJECTS_DATA

for project in ALL_PROJECTS:
    project.setdefault("card_image", project["image"])
    project.setdefault("cover_image", project["card_image"])
    project.setdefault("gallery", [project["cover_image"]])
    project.setdefault("role", project["subtitle"])
    project.setdefault("highlights", project["tags"])
    project.setdefault("tools", project["tags"])


UX_VISIBLE_CARDS = 3
UX_MAX_START = max(0, len(PROJECTS_UX) - UX_VISIBLE_CARDS)

if "ux_carousel_start" not in st.session_state:
    st.session_state["ux_carousel_start"] = 0

if "active_project_index" not in st.session_state:
    st.session_state["active_project_index"] = None


@st.dialog("Projekt", width="large")
def project_dialog(project: dict) -> None:
    project_index = next(
        (
            index
            for index, item in enumerate(ALL_PROJECTS)
            if item["title"] == project["title"]
        ),
        0,
    )

    project_key = (
        project["title"]
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("·", "_")
    )

    gallery = project.get("gallery") or [project["cover_image"]]
    gallery_index_key = f"gallery_index_{project_key}"

    if gallery_index_key not in st.session_state:
        st.session_state[gallery_index_key] = 0

    current_image_index = (
        st.session_state[gallery_index_key] % len(gallery)
    )

    current_image = get_image_data_url(
        gallery[current_image_index]
    )

    # Hauptbild über die volle Dialogbreite
    st.html(
        f"""
        <div class="case-image-frame">
            <img
                src="{current_image}"
                alt="{html.escape(project['title'])} –
                     Ansicht {current_image_index + 1}"
            >
        </div>

        <div class="case-counter">
            Bild {current_image_index + 1} von {len(gallery)}
        </div>
        """
    )

    # Navigation für Bilder innerhalb desselben Projekts
    if len(gallery) > 1:
        image_prev, image_count, image_next = st.columns(
            [1, 0.25, 1],
            vertical_alignment="center",
        )

        with image_prev:
            if st.button(
                "← Vorheriges Bild",
                key=f"previous_image_{project_key}",
                use_container_width=True,
            ):
                st.session_state[gallery_index_key] = (
                    current_image_index - 1
                ) % len(gallery)
                st.rerun()

        with image_count:
            st.html(
                f"""
                <div class="case-counter">
                    {current_image_index + 1} / {len(gallery)}
                </div>
                """
            )

        with image_next:
            if st.button(
                "Nächstes Bild →",
                key=f"next_image_{project_key}",
                use_container_width=True,
            ):
                st.session_state[gallery_index_key] = (
                    current_image_index + 1
                ) % len(gallery)
                st.rerun()
     

    tools_html = "".join(
        f'<span class="case-chip">{html.escape(tool)}</span>'
        for tool in project.get("tools", project["tags"])
    )

    highlights_html = "".join(
        f"""
        <li>
            <span class="case-check">✓</span>
            {html.escape(highlight)}
        </li>
        """
        for highlight in project.get(
            "highlights",
            project["tags"],
        )
    )

    # Beschreibung unterhalb der Galerie
    st.html(
        f"""
        <div class="case-description-grid">
            <section>
                <h4>Über das Projekt</h4>
                <p>{html.escape(project["description"])}</p>
            </section>

            <section>
                <h4>Meine Rolle</h4>
                <p>
                    {html.escape(
                        project.get("role", project["subtitle"])
                    )}
                </p>

                <h4 class="case-tools-heading">
                    Tools & Technologien
                </h4>

                <div class="case-chip-row">
                    {tools_html}
                </div>
            </section>

            <section>
                <h4>Highlights</h4>
                <ul class="case-highlights">
                    {highlights_html}
                </ul>
            </section>
        </div>
        """
    )

    if project.get("demo_url"):
        st.link_button(
            "🚀 PlatePilot App öffnen",
            project["demo_url"],
            use_container_width=False,
        )


    # Footer: zwischen Projekten wechseln
    st.html('<div class="case-project-footer-divider"></div>')

    previous_project_index = (
        project_index - 1
    ) % len(ALL_PROJECTS)

    next_project_index = (
        project_index + 1
    ) % len(ALL_PROJECTS)

    footer_left, footer_center, footer_right = st.columns(
        [1, 0.22, 1],
        vertical_alignment="center",
    )

    with footer_left:
        if st.button(
            "← Vorheriges Projekt",
            key=f"previous_project_{project_key}",
            use_container_width=True,
        ):
            st.session_state["active_project_index"] = (
                previous_project_index
            )
            st.rerun()

    with footer_center:
        st.html(
            f"""
            <div class="case-project-counter">
                {project_index + 1} / {len(ALL_PROJECTS)}
            </div>
            """
        )

    with footer_right:
        if st.button(
            "Nächstes Projekt →",
            key=f"next_project_{project_key}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["active_project_index"] = (
                next_project_index
            )
            st.rerun()


def project_card(project: dict) -> None:
    image_src = get_image_data_url(project["card_image"])

    tags = "".join(
        f'<span class="project-tag">{html.escape(tag)}</span>'
        for tag in project["tags"]
    )

    project_key = (
        project["title"]
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("·", "_")
        .replace(".", "_")
    )

    # Karte und Streamlit-Button liegen in einem gemeinsamen Container.
    # Dadurch kann CSS alle Karten gleich hoch machen und den Button
    # zuverlässig am unteren Rand ausrichten.
    with st.container(key=f"project_card_{project_key}"):
        st.html(
            f"""
            <article class="project-card">

                <div class="project-image-wrapper">
                    <img
                        src="{image_src}"
                        alt="{html.escape(project['title'])}"
                    >
                </div>

                <div class="project-content">
                    <h3>{html.escape(project['title'])}</h3>
                    <p class="project-subtitle">{html.escape(project['subtitle'])}</p>
                    <p class="project-description">{html.escape(project['description'])}</p>
                    <div class="project-tags">{tags}</div>
                </div>
            </article>
            """
        )

        if st.button(
            "Projekt ansehen →",
            key=f"open_project_{project['title']}",
            use_container_width=True,
        ):
            st.session_state["active_project_index"] = ALL_PROJECTS.index(project)
            st.rerun()


def section_header(kicker: str, title: str, text: str = "") -> None:
    st.html(
        f"""
        <div class="section-heading">
            <span>{html.escape(kicker)}</span>
            <h2>{html.escape(title)}</h2>
            {f'<p>{html.escape(text)}</p>' if text else ''}
        </div>
        """
    )


# Custom portfolio header. Replace links when the pages are ready.
st.html(
    """
    <header class="site-header">
        <a class="brand" href="#home">
            <span class="brand-mark">YP</span>
            <span>YANA PFALZGRAF</span>
        </a>
        <nav>
            <a href="#about">Über mich</a>
            <a href="#projects">Projekte</a>
            <a href="#skills">Skills</a>
        </nav>
        <a class="header-cta" href="#contact">Kontakt</a>
    </header>
    """
)

# Hero
st.html('<span id="home" class="anchor"></span>')
hero_text, hero_visual = st.columns([1.08, 0.92], gap="large", vertical_alignment="center")

with hero_text:
    st.html(
        """
        <section class="hero-copy">
            <p class="eyebrow">HALLO, ICH BIN YANA</p>
            <h1>Data Analystin<br><span>mit UX-Hintergrund</span></h1>
            <p class="hero-lead">
                Ich verbinde <b> über zehn Jahre Erfahrung </b> in der Entwicklung digitaler
                Produkte mit moderner Datenanalyse – für verständliche Insights und
                fundierte Produktentscheidungen.
            </p>
            <div class="hero-actions">
                <a class="button primary" href="#projects">Meine Projekte ansehen →</a>
                <a class="button secondary" href="#about">Über mich</a>
            </div>
        </section>
        """
    )

with hero_visual:
    st.html(
        f"""
        <div class="portrait-wrap">
            <img
                src="data:image/jpeg;base64,{portrait_base64}"
                class="portrait-image"
                alt="Portrait von Yana Pfalzgraf"
            >
        </div>
        """
    )

# Kompetenzkarten und End-to-End-Prozess mit lokalen Lucide-SVGs
st.html(
    f"""
    <section class="expertise-section" aria-label="Erfahrung und Arbeitsweise">
        <div class="expertise-cards">
            <article class="expertise-card">
                <div class="expertise-icon" aria-hidden="true">
                    <img src="{clock_icon}" alt="">
                </div>
                <div class="expertise-card-copy">
                    <p class="expertise-number">10+</p>
                    <h3>Jahre Erfahrung</h3>
                    <p>Mehr als ein Jahrzehnt in UX/UI und digitalen Produkten – von der Idee bis zum messbaren Impact.</p>
                </div>
            </article>

            <article class="expertise-card">
                <div class="expertise-icon" aria-hidden="true">
                    <img src="{workflow_icon}" alt="">
                </div>
                <div class="expertise-card-copy">
                    <p class="expertise-kicker">Ganzheitlich arbeiten</p>
                    <h3>End-to-End Denken</h3>
                    <p>Vom Nutzerverständnis über Datenanalyse bis zur Umsetzung und kontinuierlichen Optimierung.</p>
                </div>
            </article>

            <article class="expertise-card">
                <div class="expertise-icon" aria-hidden="true">
                    <img src="{chart_icon}" alt="">
                </div>
                <div class="expertise-card-copy">
                    <p class="expertise-kicker">Zwei Perspektiven</p>
                    <h3>Daten. Mensch. Produkt.</h3>
                    <p>Ich verbinde analytische Erkenntnisse mit Nutzerbedürfnissen und klaren Produktentscheidungen.</p>
                </div>
            </article>
        </div>

        <div class="process-panel">
            <p class="process-eyebrow">MEIN ANSATZ: END-TO-END &amp; NUTZERZENTRIERT</p>
            <div class="process-flow">
                <div class="process-step">
                    <div class="process-icon" aria-hidden="true">
                        <img src="{users_icon}" alt="">
                    </div>
                    <h4>Verstehen</h4>
                    <p>Nutzerbedürfnisse und Geschäftsziele erfassen</p>
                </div>

                <span class="process-arrow" aria-hidden="true">→</span>

                <div class="process-step">
                    <div class="process-icon" aria-hidden="true">
                        <img src="{search_icon}" alt="">
                    </div>
                    <h4>Analysieren</h4>
                    <p>Daten untersuchen und Muster erkennen</p>
                </div>

                <span class="process-arrow" aria-hidden="true">→</span>

                <div class="process-step">
                    <div class="process-icon" aria-hidden="true">
                        <img src="{lightbulb_icon}" alt="">
                    </div>
                    <h4>Insights ableiten</h4>
                    <p>Komplexe Daten in klare Erkenntnisse übersetzen</p>
                </div>

                <span class="process-arrow" aria-hidden="true">→</span>

                <div class="process-step">
                    <div class="process-icon" aria-hidden="true">
                        <img src="{target_icon}" alt="">
                    </div>
                    <h4>Entscheiden</h4>
                    <p>Empfehlungen aussprechen und Prioritäten setzen</p>
                </div>

                <span class="process-arrow" aria-hidden="true">→</span>

                <div class="process-step">
                    <div class="process-icon" aria-hidden="true">
                        <img src="{growth_icon}" alt="">
                    </div>
                    <h4>Optimieren</h4>
                    <p>Maßnahmen begleiten und Wirkung messen</p>
                </div>
            </div>
        </div>
    </section>
    """
)


# About & skills
st.html('<span id="about" class="anchor"></span>')
about_col, skills_col = st.columns([0.95, 1.05], gap="large")

with about_col:
    section_header("PROFIL", "Über mich")
    st.markdown(
        """
Ich bin **Data Analystin mit einem starken Fundament in UX/UI Design** und
über zehn Jahren Erfahrung in der Entwicklung digitaler Produkte. Dabei habe
ich gelernt, komplexe Anforderungen zu strukturieren, Nutzerbedürfnisse zu
verstehen und verständliche Lösungen zu gestalten.

Mit meiner Weiterbildung in **Data Science & Analytics** habe ich diese
Erfahrung um Python, Statistik, Machine Learning und Datenvisualisierung
erweitert. Heute verbinde ich analytisches Denken mit nutzerzentrierter
Produktentwicklung, um Daten in klare Erkenntnisse und sinnvolle
Entscheidungsgrundlagen zu übersetzen.

Besonders interessieren mich **Product Analytics, Data Analytics und
datenbasierte digitale Produkte** – also Aufgaben an der Schnittstelle von
Mensch, Daten und Technologie.
        """
    )

with skills_col:
    st.html('<span id="skills" class="anchor"></span>')
    section_header("TOOLKIT", "Meine Kompetenzen")
    skills = [
        "Python", "Pandas", "SQL", "Excel", "Power BI",
        "Data Visualization", "Explorative Analyse", "Scrum Master", "Streamlit", "Statistik", "Machine Learning",
        "UX Research", "UI Design", "Prototyping", "Figma",
        "Information Architecture", "Design Systems", "Stakeholder-Kommunikation",
    ]
    st.html(
        '<div class="skills-grid">'
        + "".join(f'<span>{html.escape(skill)}</span>' for skill in skills)
        + "</div>"
    )

# Projects
st.html('<span id="projects" class="anchor"></span>')
section_header(
    "AUSGEWÄHLTE ARBEITEN",
    "Projekte",
    "Data-Science-Kompetenzen und UX-Erfahrung neue in einer gemeinsamen Produktperspektive.",
)

st.html('<div class="project-category data"><span>DATA SCIENCE & ANALYTICS</span></div>')

# Exakt drei Data-Science-Projekte: statisches Grid ohne Pfeile und Punkte.
data_cols = st.columns(3, gap="medium")
for column, project in zip(data_cols, PROJECTS_DATA):
    with column:
        project_card(project)



st.html('<div class="project-category"><span>UX/UI & PRODUCT DESIGN</span></div>')

# Desktop: drei Karten sichtbar. Mit den Pfeilen wird jeweils um eine Karte verschoben.
ux_start = min(
    max(0, st.session_state["ux_carousel_start"]),
    UX_MAX_START,
)
st.session_state["ux_carousel_start"] = ux_start
visible_ux_projects = PROJECTS_UX[ux_start:ux_start + UX_VISIBLE_CARDS]

with st.container(key="ux_project_carousel"):
    left_arrow, card_1, card_2, card_3, right_arrow = st.columns(
        [0.13, 1, 1, 1, 0.13],
        gap="medium",
        vertical_alignment="center",
    )

    with left_arrow:
        if st.button(
            "←",
            key="ux_carousel_previous",
            disabled=ux_start == 0,
            help="Vorherige Projekte",
            use_container_width=True,
        ):
            st.session_state["ux_carousel_start"] = max(0, ux_start - 1)
            st.rerun()

    for column, project in zip(
        (card_1, card_2, card_3),
        visible_ux_projects,
    ):
        with column:
            project_card(project)

    with right_arrow:
        if st.button(
            "→",
            key="ux_carousel_next",
            disabled=ux_start >= UX_MAX_START,
            help="Weitere Projekte",
            use_container_width=True,
        ):
            st.session_state["ux_carousel_start"] = min(
                UX_MAX_START,
                ux_start + 1,
            )
            st.rerun()

    if UX_MAX_START > 0:
        dots = "".join(
            '<span class="carousel-dot active" aria-current="true"></span>'
            if index == ux_start
            else '<span class="carousel-dot"></span>'
            for index in range(UX_MAX_START + 1)
        )
        st.html(
            f'<div class="carousel-dots" aria-label="Carousel-Position">{dots}</div>'
        )

# Der Dialog wird nur auf Top-Level geöffnet.
# Dadurch können Projekte gewechselt werden, ohne Dialoge zu verschachteln.
active_project_index = st.session_state.get("active_project_index")
if active_project_index is not None:
    project_dialog(ALL_PROJECTS[active_project_index])

# CTA
st.html('<span id="contact" class="anchor"></span>')

with st.container(key="contact_banner"):
    contact_copy, contact_action = st.columns(
        [4.2, 1.25],
        gap="large",
        vertical_alignment="center",
    )

    with contact_copy:
        st.html(
            """
            <div class="contact-banner-copy">
                <p class="eyebrow">KONTAKT</p>
                <h2>Lass uns gemeinsam Zukunft gestalten.</h2>
                <p>
                    Ich freue mich über Austausch, neue Herausforderungen
                    und passende Rollen im Bereich Data Analytics.
                </p>
            </div>
            """
        )

    with contact_action:
        st.button(
            "Zum Formular →",
            key="open_portfolio_chat_button",
            type="primary",
            use_container_width=True,
            on_click=open_contact_form,
        )
        st.caption("Öffnet das Kontaktformular.")

# Kontaktformular und Chatbot bleiben vollständig voneinander getrennt.
if st.session_state.get("contact_form_open", False):
    contact_form_dialog(
        portrait_data_url=f"data:image/jpeg;base64,{portrait_base64}"
    )

# Der Portfolio-Chat ist als schwebendes, beim Scrollen sichtbares Element verfügbar.
render_floating_chat(
    portrait_data_url=f"data:image/jpeg;base64,{portrait_base64}"
)


st.html(
    """
  <footer>
    <div>
        <strong>LINKS</strong>

        <p>
            <a
                href="https://www.linkedin.com/in/yana-pfalzgraf-610669136/"
                target="_blank"
                rel="noopener noreferrer"
            >
                LinkedIn
            </a>

            &middot;

            <a
                href="https://www.xing.com/profile/Yana_Pfalzgraf"
                target="_blank"
                rel="noopener noreferrer"
            >
                XING
            </a>

            &middot;

            <a
                href="https://github.com/yanapfalzgraf"
                target="_blank"
                rel="noopener noreferrer"
            >
                GitHub
            </a>
        </p>
    </div>
</footer>
    """
)