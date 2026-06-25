import pandas as pd
import numpy as np

def get_recommendations(df: pd.DataFrame,
                        u_cat: list, u_attr: list, u_price: int,
                        u_lat: float, u_lon: float, d_max: float = 50.0,
                        alpha: float = 0.6, w_cat: float = 4.0, w_attr: float = 3.0, w_price: float = 2.0, w_dist: float = 1.0,
                        top_n: int = 10) -> pd.DataFrame:
    
    """
    Berechnet die Top N Restaurant-Empfehlungen basierend auf hybriden Scores.
    """
    
    # Normierung von User-Gewichten
    w_sum = w_cat + w_attr + w_price + w_dist
    if w_sum == 0:
        w_sum = 1e-9 # Division durch Null vermeiden
    w1, w2, w3, w4 = w_cat/w_sum, w_attr/w_sum, w_price/w_sum, w_dist/w_sum

    # Filter 1: Bounding-Box (schneller Vorfilter)
    lat_offset = d_max/111.32 # 1 Breitengrad = ca. 111.32 km
    lon_offset = d_max/(111.32 * np.cos(np.radians(u_lat)))
    df_filtered = df[
        (df['latitude'] >= u_lat - lat_offset) &
        (df['latitude'] <= u_lat + lat_offset) &
        (df['longitude'] >= u_lon - lon_offset) &
        (df['longitude'] <= u_lon + lon_offset)
    ].copy()
    if df_filtered.empty:
        return df_filtered

    # Filter 2 (genauer Haversine-Distanz-Filter)
    R = 6371.0 # Erdradius in km
    lat1, lon1 = np.radians(u_lat), np.radians(u_lon)
    lat2, lon2 = np.radians(df_filtered['latitude'].values), np.radians(df_filtered['longitude'].values)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    df_filtered['calc_distance'] = R * c
    df_filtered = df_filtered[df_filtered['calc_distance'] <= d_max].copy()
    if df_filtered.empty:
        return df_filtered

    
    # BERECHNUNG DER PFS-TEILSCORES

    # Vorbereitung Vektor-Matrizen
    cat_matrix = np.stack(df_filtered['categories_vector'].values)
    attr_matrix = np.stack(df_filtered['attributes_vector'].values)
    u_cat_vec = np.array(u_cat)
    u_attr_vec = np.array(u_attr)

    # S_CAT (Cosine Similarity)
    norm_u_cat = np.linalg.norm(u_cat_vec)
    if norm_u_cat > 0:
        norm_rest_cat = np.linalg.norm(cat_matrix, axis=1)
        s_cat = cat_matrix.dot(u_cat_vec) / (norm_u_cat * norm_rest_cat + 1e-9)
    else:
        s_cat = np.zeros(len(df_filtered))

    # S_ATTR (Recall, hier Ratio Match)
    sum_u_attr = np.sum(u_attr_vec) # Anzahl geforderter Attribute vom User
    if sum_u_attr > 0:
        s_attr = attr_matrix.dot(u_attr_vec) / sum_u_attr # Trefferquote pro Restaurant
    else:
        s_attr = np.ones(len(df_filtered)) # User fordert keine speziellen Attribute -> perfekter Match -> 1
    
    # S_PRICE
    price_diff = df_filtered['PriceLevel'].values - u_price
    s_price = np.where(price_diff >= 0, 1 - (1/3) * price_diff, 1.0 - (1/6) * np.abs(price_diff)) # Fallunterscheidung Penalty
    s_price = np.clip(s_price, 0.0, 1.0) # zur Sicherheit trunkieren
  
    # S_DIST
    s_dist = 1.0 - np.sqrt(df_filtered['calc_distance'].values / d_max)

    # PFS GESAMT
    pfs = (w1 * s_cat) + (w2 * s_attr) + (w3 * s_price) + (w4 * s_dist)


    # RANKING UND AUSGABE VON TOP N EINTRÄGEN
    
    #df_filtered['SCORE'] = (alpha * pfs) + ((1 - alpha) * df_filtered['GPS'].values)
   # return df_filtered.sort_values(by='SCORE', ascending=False).head(top_n)
    
    #return df_filtered.sort_values(by='SCORE', ascending=False)
    df_filtered['SCORE'] = (alpha * pfs) + ((1 - alpha) * df_filtered['GPS'].values)

    df_filtered["category_score"] = s_cat
    df_filtered["attribute_score"] = s_attr
    df_filtered["price_score"] = s_price
    df_filtered["distance_score"] = s_dist
    df_filtered["popularity_score"] = df_filtered["GPS"]
    df_filtered["final_score"] = df_filtered["SCORE"]

    return df_filtered.sort_values(by="SCORE", ascending=False).head(top_n)