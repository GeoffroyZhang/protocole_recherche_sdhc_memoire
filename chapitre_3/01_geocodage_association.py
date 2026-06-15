# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 17:03:54 2026

@author: Zhang

Objectif : Géocoder les adresses des associations afin de transformer les adresses en coordonnées GPS pour l'export dans Qgis afin de projeter une carte

Output : un CSV enrichi des coordonnées 

"""

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from pathlib import Path


# 1. Chargement du CSV 
csvf = r"CHEMIN_A_DEFINIR"

df = pd.read_csv(csvf)


# 2. Nettoyage du code postal

# pandas lit parfois les codes postaux comme des nombres flottants (ex: 75013.0)
# on les convertit en texte et on supprime le ".0" superflu
df["asso_code_postal"] = df["asso_code_postal"].astype(str).str.replace(".0", "", regex=False)


# 3. Construction de l'adresse complète

# On assemble rue + code postal + commune en une seule colonne
# C'est cette chaîne de texte qui sera envoyée au géocodeur
# On ajoute ", France" pour affiner les résultats
df["adresse_complete"] = (
    df["asso_rue"].astype(str) + ", " +
    df["asso_code_postal"].astype(str) + ", " +
    df["asso_commune"].astype(str) + ", France"
)


# 4. Configuration du géocodeur

# user_agent : OpenStreetMap demande de s'identifier avec un nom unique
# timeout : on attend jusqu'à 60 secondes avant d'abandonner une requête
geolocator = Nominatim(user_agent="memoire_sdhc_zhang", timeout=60)

# RateLimiter impose un délai de 3 secondes entre chaque requête
# C'est la règle d'usage d'OpenStreetMap pour ne pas se faire bloquer
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=3)


# 5. Fonction de géocodage

def get_coords(adresse):
    """
    Prend une adresse en texte, retourne la latitude et longitude.
    Si l'adresse n'est pas trouvée ou qu'une erreur survient,
    retourne None pour les deux valeurs.
    """
    print(f"Géocodage : {adresse}")
    try:
        location = geocode(adresse)
        if location:
            return pd.Series([location.latitude, location.longitude])
        else:
            # L'adresse n'a pas été trouvée, on retourne des valeurs vides
            print(f"Non trouvée : {adresse}")
            return pd.Series([None, None])
    except (GeocoderTimedOut, GeocoderUnavailable):
        # Le serveur n'a pas répondu, on retourne des valeurs vides
        print(f"Erreur serveur : {adresse}")
        return pd.Series([None, None])


# 6. Application du géocodage 

# On applique la fonction à chaque ligne du tableau
# Les résultats sont stockés dans deux nouvelles colonnes : latitude et longitude
df[["latitude", "longitude"]] = df["adresse_complete"].apply(get_coords)


# 7. Bilan 

nb_total = len(df)
nb_geocodes = df["latitude"].notna().sum()
nb_echecs = nb_total - nb_geocodes

print(f"Bilan : {nb_geocodes}/{nb_total} associations géocodées.")
if nb_echecs > 0:
    print(f"{nb_echecs} adresse(s) non trouvée(s) :")
    print(df[df["latitude"].isna()][["nom_association", "adresse_complete"]])


# 8. Sauvegarde du CSV et export

# Chemin de sortie
chemin_sortie = Path(r"CHEMIN_A_DEFINIR")

# On sauvegarde le tableau complet avec les nouvelles colonnes latitude/longitude
# Ce fichier sera importé directement dans QGIS
output = chemin_sortie/"association_geocode.csv"
df.to_csv(output, index=False)
print(f"Fichier sauvegardé : {output}")