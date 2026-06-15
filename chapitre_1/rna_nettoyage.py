# -*- coding: utf-8 -*-
"""
Created on Fri Feb  6 12:19:26 2026

@author: Zhang
"""

"""
Objectif : Nettoyer le jeu de données du RNA afin de trouver les associations chinoises

→ Utilisation de mots-clés afin de filtrer les asssociations


"""
import pandas as pd 
import re # librairie pour les regex

# low_memory -> permet de lire le fichier csv en petits morceaux pour les fichiers volumineux
df = pd.read_csv("CHEMIN_A_DEFINIR", sep = ",", encoding = "utf-8", low_memory = False)

df.head()
df.shape
df.info
df.describe
df.columns

# Compte le nb de NA dans la colonne siteweb 
NA_count = df["siteweb"].isna().sum()

df["siteweb"].count() # Seulement 87082 associations ont indiqué leur site web 

"""
df_site2 = df[df["siteweb"].notna() & (df["siteweb"].str.strip() != "")]
"""
# Création d'un nouveau dataframe
# Filtrage des associations qui n'ont pas de sites web
df_site = df[df["siteweb"].notna()]

# Création d'un dataframe
# On sélectionne les colonnes que l'on veut analyser 
df_selcol = df_site[["date_creat", "titre", "titre_court", "objet", "adrs_libcommune", "adrg_libvoie", "adrg_codepostal", "siteweb" ]]

keywords_chine = ["sino", "mandarin", "cantonais", "wenzhou", "qingtian","zhejiang", "guangdong", "franco-chinoise", "sino-française", "teochew", "fujian", "diaspora chinoise", "communauté chinoise"]
# Exclusion des mots trop génériques comme "chine", "chinois", "chinoise"
# keywords_chine2 = ["diaspora chinoise"] → Aucune association n'a au sein de sa raison sociale le terme "diaspora chinoise"


# Créer un pattern regex
pattern = "|".join(keywords_chine)

# Création d'une nouvelle colonne texte 
# Contient les titres des associations 
# On réunit tout pour faciliter l'analyse 
df_selcol["texte"] = df_selcol["titre"].fillna("") + " " + df_selcol["objet"].fillna("")

# Fonction pour nettoyer le texte
def clean_text(text):
    """
    Fonction qui permet de nettoyer le texte 
    
    Utilsation d'expressions régulières
    """
    text = str(text).lower()  # tout en minuscules pour le filtre
    text = re.sub(r"[^a-z0-9\s]", " ", text)  # enlever ponctuation
    text = re.sub(r"\s+", " ", text).strip()  # nettoyer espaces multiples
    return text

# Application de la fonction clean_text sur le colonne texte
df_selcol["texte_clean"] = df_selcol["texte"].apply(clean_text)

# Création d'une colonne booléenne 
# case=False -> ignore majuscules/minuscules 
# na=False -> les lignes sont considérées comme fausses 
# True si au moins un mot du patter est dans la ligne 
df_selcol["mention_chine"] = df_selcol["texte_clean"].str.contains(pattern, case=False, na=False)

# Compte le nombre d'association ayant les mots clés
print("Nombre d'associations liées à la Chine :", df_selcol["mention_chine"].sum())

# Création d'un dataframe
# Contient les association qui mentionnent la Chine 
# Filtre automatiquement sur les True 
df_chine = df_selcol[df_selcol["mention_chine"]]

# Création d'un nouveau df 
# Suppression des colonnes qui ne nous intéresse pas 
association_chine = df_chine[["date_creat", "titre", "titre_court", "objet", "adrs_libcommune", "adrg_libvoie", "adrg_codepostal", "siteweb"]]

# Liste des nom de domaine à exclure de l'analyse 
# En particulier les réseaux sociaux et les annuaires 
exclure = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "youtube.com", "pagesjaunes.fr", "@", "helloasso", " ", ]

# Création du pattern
pattern_exclure = "|".join(exclure)


def clean_siteweb(site):
    """
     Fonction pour invalider les sites qui ne correspondent pas 
    """
    if pd.isna(site) or site.strip() == "":
        return "invalide"
    # re.IGNORECASE : pour reconnaître les mots malgré la casse 
    if re.search(pattern_exclure, site, re.IGNORECASE): 
        return "invalide"
    return site
  
# Application de la fonction à la colonne siteweb 
association_chine["siteweb_valide"] = association_chine["siteweb"].apply(clean_siteweb)

# On retire les sites invalides 
association_chine = association_chine[association_chine["siteweb_valide"] != "invalide"]

# Exclusion de cas particulier 
association_chine = association_chine[association_chine["siteweb_valide"] != "0669016818"]
association_chine = association_chine[association_chine["siteweb_valide"] != "EMERGING ASIAN ARTIST AWARD"]

# On enlève une colonne pour éviter la redondance 
association_chine = association_chine[["date_creat", "titre", "titre_court", "objet", "adrs_libcommune", "adrg_libvoie", "adrg_codepostal", "siteweb"]]

csv_assoChine = association_chine.to_csv("rna_waldec_assoChineFiltre.csv", sep=",",index=False, encoding="utf-8")


