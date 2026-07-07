import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor

# csv lesen
df = pd.read_excel(
    "autoscout24_new.xlsx",
    sheet_name="autoscout24"   # Name deines Tabellenblatts
)

#csv zeigt erste 5 zeilen 
df.head()

top5 = [
    "Volkswagen",
    "Opel",
    "Ford",
    "Skoda",
    "Renault"
]

df_top5 = df[df["FzgMarke"].isin(top5)] #nimmt die Spalte FzgMarke und prüft nach diese 5 Marke
df_top5 = df_top5.dropna()
#print(df_top5["FzgMarke"].value_counts()) #zähle wie oft jeder unterschiedlice Wert in dieser Spalte vorkommt

#Kontrollieren, wie viele Datensätze übrig sind
#print(df_top5.shape)

#Zielvariable: Preis
y = df_top5["Preis"]

#Features
X = df_top5[
    [
        "Kmstand",
        "Leistung",
        "Baujahr",
        "Getriebe",
        "Kraftstoff_diesel"
    ]
]

y = df_top5["Preis"]

#welche spalten gibt es?
#print(df_top5.dtypes)

#Textspalten umwandeln
X = pd.get_dummies(
    X,
    columns=["Getriebe", "Kraftstoff_diesel"],
    drop_first=True
)

#Kontrolieren
#print(X.head())
#print(X.dtypes)


X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print("Trainingsdaten:", X_train.shape)
print("Testdaten:", X_test.shape)

#Trainingsdaten: 16.820 Datensätze (80 %)
#Testdaten: 4.205 Datensätze (20 %)
#15 Features (3 numerische + 12 Dummy-Variablen)

#Erste Modell trainieren

modell = LinearRegression()

modell.fit(X_train, y_train)
y_pred = modell.predict(X_test)

print("Lineare Regression erfolgreich trainiert.")
#print(X.isna().sum())

#Bewertung des Modells
# Vorhersagen
y_pred = modell.predict(X_test)

# Kennzahlen berechnen
mae = mean_absolute_error(y_test, y_pred)
rmse = mean_squared_error(y_test, y_pred) ** 0.5
r2 = r2_score(y_test, y_pred)

#print(f"MAE : {mae:.2f}") #durchschnitt.fehler der vorhersage in Euro
#print(f"RMSE: {rmse:.2f}") #wie stark das Modell große Fehler bestraft
#print(f"R²  : {r2:.3f}") #wie gut das Modell die Preisunterschiede erklären 

#MAE = 2.981,83 €
# Der mittlere absolute Fehler (MAE) beträgt 2.981,83 €. Das bedeutet, 
#dass die vorhergesagten Fahrzeugpreise im Durchschnitt 
#um etwa 2.982 € vom tatsächlichen Verkaufspreis abweichen.

#RMSE = 4.862,52 €
#Der RMSE ist höher als der MAE, weil größere Fehler stärker gewichtet werden.
#Der RMSE beträgt 4.862,52 €. Diese Kennzahl bestraft größere Vorhersagefehler 
#stärker und zeigt, dass einzelne Fahrzeuge deutlich schlechter vorhergesagt 
# werden als der Durchschnitt.

#R² = 0,762
#Das Modell kann rund 76,2 % der Preisunterschiede zwischen den Fahrzeugen erklären.

#/////////// Random PForest Regressor

rf = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

rf.fit(X_train, y_train)

y_pred_rf = rf.predict(X_test)

mae_rf = mean_absolute_error(y_test, y_pred_rf)
rmse_rf = mean_squared_error(y_test, y_pred_rf) ** 0.5
r2_rf = r2_score(y_test, y_pred_rf)

print("\nRandom Forest")
print(f"MAE : {mae_rf:.2f}")
print(f"RMSE: {rmse_rf:.2f}")
print(f"R²  : {r2_rf:.3f}")

# =========================
# Ergebnisse für Power BI
# =========================

# 1) Vorhersagen vs. tatsächliche Preise
ml_predictions = pd.DataFrame({
    "Tatsaechlicher_Preis": y_test.values,
    "Vorhergesagter_Preis": y_pred_rf
})

# 2) Feature Importance
feature_importance = pd.DataFrame({
    "Feature": X.columns,
    "Importance": rf.feature_importances_
}).sort_values(by="Importance", ascending=False)

# 3) Modellmetriken
ml_metrics = pd.DataFrame({
    "Modell": ["Random Forest"],
    "MAE": [mae_rf],
    "RMSE": [rmse_rf],
    "R2": [r2_rf]
})

# Excel-Datei für Power BI exportieren
with pd.ExcelWriter("ml_ergebnisse.xlsx") as writer:
    ml_predictions.to_excel(writer, sheet_name="Predictions", index=False)
    feature_importance.to_excel(writer, sheet_name="FeatureImportance", index=False)
    ml_metrics.to_excel(writer, sheet_name="Metrics", index=False)

print("ML-Ergebnisse wurden als ml_ergebnisse.xlsx exportiert.")

