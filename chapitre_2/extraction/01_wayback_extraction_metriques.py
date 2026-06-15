"""
Script d'extraction des métriques
depuis les fichiers HTML collectés par le script de collecte des snapshots de la Wayback Machine
"""

from pathlib import Path
from bs4 import BeautifulSoup
import json
import csv 
import trafilatura

# Pour l'import dans ma BDD
ids_sites = {
    "lajcf.fr"                          : 1,
    "pierreducerf.com"                  : 2,
    "culture-oushi.com"                 : 3,
    "asiafc.fr"                         : 4,
    "cffc.fr"                           : 5,
    "asso-franco-chinois.fr"            : 6,
    "chinemontargis.fr"                 : 7,
    "mcna.fr"                           : 8,
    "atout-chine.fr"                    : 9,
    "aeafc.fr"                          : 10,
    "ausuddesnuages.org"                : 11,
    "acmfc.fr"                          : 12,
    "aacf1985.org"                      : 13,
    "affclyon.org"                      : 14,
    "affcannecy.org"                    : 15,
    "tpfc.fr"                           : 16,
    "aecfc.org"                         : 17,
    "bureauafc92.wixsite.com"           : 18,
    "aslc-paris.org"                    : 19,
    "maisonculturellechinoise.fr"       : 20,
    "heyi.fr"                           : 21,
    "franco-chinois.fr"                 : 22,
    "decouvertedelachine.com"           : 23,
    "ateliersfrancochinois.com"         : 24,
    "alpi-isere.com"                    : 25,
    "huayuan.fr"                        : 26,
    "chinois-en-savoie.fr"              : 27,
    "aclyr.org"                         : 28,
    "asso-mugua.fr"                     : 29,
    "hanfufrance.com"                   : 30,
    "asso-soleil.com"                   : 31,
    "chinawawa.fr"                      : 32,
    "jeunesteochew.com"                 : 33,
    "dansedelion.fr"                    : 34,
    "aixintuan.fr"                      : 35,
    "afc92.com"                         : 36,
    "amicaleteochew.fr"                 : 37,
    "frhuaqiao.com"                     : 38,
    "acrf.paris"                        : 39,
    "uchrafr.com"                       : 40,
    "adefc.org"                         : 41,
    "liaoning-france.com"               : 42,
    "calligraphieetculturechinoise.fr"  : 43,
    "acwf.fr"                           : 44,
    "jeunechinoisdeurope.com"           : 45,
    "huiji.org"                         : 46
}

# Dictionnaire associant les indices de détection aux noms lisibles
# C'est une liste non-exhaustive, vous pouvez en ajouter autant que vous voulez. 
cms_indices = {
    "wp-content" : "WordPress",
    "wp-includes" : "WordPress",
    "wix.com" : "Wix",
    "wixstatic" : "Wix",
    "joomla" : "Joomla",
    "drupal" : "Drupal",
    "squarespace" : "Squarespace",
    "webflow" : "Webflow",
    "jimdo" : "Jimdo",
    "weebly" : "Weebly",
    "prestashop" : "Prestashop",
    "ionos" : "Ionos",
    "sitew" : "SiteW",
    "dedecms" : "DedeCMS",
    "phpcms" : "PHPCMS",
    "discuz" : "Discuz"
    }

# Dossier contenant les archives collectées par le script 01_scraping_wayback_accueil_v3
dossier = Path(r"CHEMIN_A_DEFINIR")

chemin_csv = Path(r"CHEMIN_A_DEFINIR")

with open(chemin_csv, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)

    # En-têtes du CSV
    writer.writerow([
        "id_site",
        "domain",
        "timestamp",
        "snapshot_url",
        "date",
        "title",
        "cms", 
        "taille_octets",
        "nb_mots",
        "nb_images",
        "nb_boutons",
        "nb_liens_internes",
        "nb_liens_externes",
        "wechat",
        "linkedin",
        "instagram",
        "facebook",
        "twitter",
        "youtube",
        "weibo"
    ])

    """Si on veut ajouter d'autres métriques, il faut les ajouter dans la liste en haut."""

    # On parcourt chaque sous-dossier du dossier principal
    # Chaque sous-dossier correspond à un site (ex: lajcf.fr)
    # sorted() permet de traiter les dossiers par ordre alphabétique 
    for site_path in sorted(dossier.iterdir()):

        # On vérifie que c'est bien un dossier et pas un fichier
        if not site_path.is_dir():
            continue

        domain = site_path.name
        print(f"Traitement : {domain}")

        # On récupère tous les fichiers HTML du dossier
        # Les fichiers sont rangés dans l'ordre chronologique 
        fichiers_html = sorted(site_path.glob("*.html"))

        if not fichiers_html:
            print("Aucun fichier HTML trouvé")
            continue

        print(f"{len(fichiers_html)} fichiers HTML trouvés")

        for chemin_html in fichiers_html:
            
            try:
                # On reconstruit le nom de base pour retrouver le metadata.json correspondant
                # .stem permet d'extraire le nom du fichier sans l'extension 
                nom_base = chemin_html.stem
                chemin_metadata = site_path / f"{nom_base}_meta.json"

                # On lit le fichier HTML
                html_content = chemin_html.read_text(encoding="utf-8")

                # Instanciation d'un objet beautifulsoup
                soup = BeautifulSoup(html_content, "html.parser")

                # Images
                nb_images = len(soup.find_all("img"))

                # Boutons
                nb_boutons = (len(soup.find_all("button")) +
                len(soup.find_all("input", {"type": "button"})) +
                len(soup.find_all("input", {"type": "submit"})))
                
                # Liens 
                liens = soup.find_all("a")
                nb_liens_internes = 0
                nb_liens_externes = 0

                for lien in liens:
                    href = lien.get("href", "")
                    if href.startswith("http"): # Pour les liens externes
                        nb_liens_externes += 1
                    elif href.startswith("/") or href != "": # Pour les liens internes
                        nb_liens_internes += 1
                
                # Réseaux sociaux 
                texte_page = html_content.lower() # On met tout en minuscule pour faciliter la recherche 
                facebook  = int("facebook.com" in texte_page) # Résultat en 1 ou 0 afin de faciliter l'import dans mysql 
                instagram = int("instagram.com" in texte_page)
                youtube = int("youtube.com" in texte_page)
                twitter = int("twitter.com" in texte_page or "x.com" in texte_page)
                weibo = int("weibo.com" in texte_page)
                wechat = int("wechat.com" in texte_page or "weixin" in texte_page)
                linkedin = int("linkedin.com" in texte_page)

                # Détection du CMS
                cms = "inconnu"
                for indice, nom in cms_indices.items():
                    if indice in texte_page:
                        cms = nom
                        break

                # Calcul de la taille en octets
                taille_octets = len(html_content.encode("utf-8")) # Un caractère chinois compte pour 3 octets donc il faut prendre cela en compte 

                # Texte visible de la page
                texte = trafilatura.extract(html_content)
                nb_mots = len(texte.split()) if texte else 0

                # Timestamp
                timestamp = nom_base.replace("_", "")

                """"On peut ajouter autant de métriques que l'on veut ici."""

                print(f"{nom_base} — {taille_octets} octets")

                # On vérifie que le fichier metadata existe avant de le modifier
                if not chemin_metadata.exists():
                    print(f" Fichier metadata introuvable pour {nom_base}")
                    continue

                # On lit les métadonnées existantes
                with open(chemin_metadata, "r", encoding="utf-8") as m:
                    meta = json.load(m)

                # Ajout d'une ligne dans le csv 
                writer.writerow([
                    ids_sites.get(domain, None),
                    domain,
                    timestamp,
                    meta.get("url_snapshot",""),
                    meta.get("date", ""),
                    meta.get("titre",""), 
                    cms,
                    taille_octets, 
                    nb_mots,
                    nb_images, 
                    nb_boutons, 
                    nb_liens_internes,
                    nb_liens_externes,  
                    wechat, 
                    linkedin,
                    instagram,
                    facebook,
                    twitter,
                    youtube, 
                    weibo
                ])

                """"Ajouter d'autres métriques en haut."""
            except Exception as e:
                print(f"Une erreur s'est produite dans {nom_base} : {e}")

print("Terminé.")