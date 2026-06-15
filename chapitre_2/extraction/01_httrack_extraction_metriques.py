"""
Script d'extraction des métriques depuis les archives HTTrack
pour l'import dans la table archive_site de la base de données. 
"""

from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import trafilatura
import chardet
import csv

# Dossier contenant les archives HTTrack
dossier_httrack = Path(r"CHEMIN_A_DEFINIR")

# Fichier CSV de sortie
chemin_csv = Path(r"CHEMIN_A_DEFINIR")
chemin_csv.parent.mkdir(parents=True, exist_ok=True)

# Dictionnaire ids_sites
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

# Dictionnaire CMS
cms_indices = {
    "wp-content"  : "WordPress",
    "wp-includes" : "WordPress",
    "wix.com"     : "Wix",
    "wixstatic"   : "Wix",
    "joomla"      : "Joomla",
    "drupal"      : "Drupal",
    "squarespace" : "Squarespace",
    "webflow"     : "Webflow",
    "jimdo"       : "Jimdo",
    "weebly"      : "Weebly",
    "prestashop"  : "Prestashop",
    "ionos"       : "Ionos",
    "sitew"       : "SiteW",
    "dedecms"     : "DedeCMS",
}

# Extraction des domaines
urls = [
    "https://www.lajcf.fr",
    "https://www.pierreducerf.com",
    "https://www.culture-oushi.com",
    "https://www.asiafc.fr",
    "https://www.cffc.fr",
    "http://www.asso-franco-chinois.fr",
    "https://www.chinemontargis.fr",
    "https://www.mcna.fr",
    "https://atout-chine.fr",
    "https://aeafc.fr",
    "https://www.ausuddesnuages.org",
    "https://acmfc.fr",
    "http://aacf1985.org/aacf",
    "https://www.affclyon.org",
    "https://affcannecy.org",
    "https://www.tpfc.fr",
    "https://aecfc.org",
    "https://bureauafc92.wixsite.com/afcrueil",
    "https://aslc-paris.org",
    "https://maisonculturellechinoise.fr",
    "https://heyi.fr",
    "https://www.franco-chinois.fr",
    "https://www.decouvertedelachine.com",
    "https://www.ateliersfrancochinois.com",
    "http://alpi-isere.com",
    "https://www.huayuan.fr",
    "https://www.chinois-en-savoie.fr",
    "https://aclyr.org",
    "https://asso-mugua.fr",
    "https://hanfufrance.com",
    "https://asso-soleil.com",
    "https://www.chinawawa.fr",
    "https://www.jeunesteochew.com",
    "https://www.dansedelion.fr",
    "https://www.aixintuan.fr",
    "https://afc92.com",
    "https://amicaleteochew.fr",
    "http://www.frhuaqiao.com",
    "https://www.acrf.paris",
    "https://www.uchrafr.com",
    "http://www.adefc.org",
    "https://liaoning-france.com",
    "https://calligraphieetculturechinoise.fr",
    "https://www.acwf.fr",
]

domaines = set()
for url in urls:
    parsed = urlparse(url)
    domaines.add(parsed.netloc)


with open(chemin_csv, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)

    writer.writerow([
        "id_site",
        "domain",
        "date_archivage",
        "nom_dossier",
        "cms",
        "taille_octets",
        "nb_mots",
        "nb_images",
        "nb_boutons",
    ])

    for site_path in sorted(dossier_httrack.iterdir()):

        if not site_path.is_dir():
            continue

        nom_dossier = site_path.name
        print(f"Traitement : {nom_dossier}")

        date_brute = nom_dossier.split("_")[-1]
        date_lisible = f"{date_brute[4:]}-{date_brute[2:4]}-{date_brute[:2]}"

        dossier_site = None
        domain = None

        for sous_dossier in site_path.iterdir():
            if sous_dossier.is_dir() and sous_dossier.name in domaines:
                dossier_site = sous_dossier
                domain = sous_dossier.name
                break

        if dossier_site is None:
            print("Aucun dossier de site trouvé")
            continue

        print(f"Domaine : {domain}")

        domain_clean = domain[4:] if domain.startswith("www.") else domain
        id_site = ids_sites.get(domain_clean, None)

        fichiers_html = sorted(dossier_site.rglob("*.html"))

        if not fichiers_html:
            print("Aucun fichier HTML trouvé")
            continue

        print(f"{len(fichiers_html)} fichiers HTML trouvés")

        taille_octets_total = 0
        nb_mots_total = 0
        nb_images_total = 0
        nb_boutons_total = 0
        cms = "Inconnu"

        for chemin_html in fichiers_html:

            try:
                raw = chemin_html.read_bytes()
                detection = chardet.detect(raw)
                encodage = detection["encoding"] or "utf-8"
                html_content = raw.decode(encodage, errors="ignore")

                soup = BeautifulSoup(html_content, "html.parser")

                taille_octets_total += len(html_content.encode("utf-8"))
                nb_images_total += len(soup.find_all("img"))
                nb_boutons_total += (
                    len(soup.find_all("button")) +
                    len(soup.find_all("input", {"type": "button"})) +
                    len(soup.find_all("input", {"type": "submit"}))
                )

                texte = trafilatura.extract(html_content)
                if texte:
                    nb_mots_total += len(texte.split())
                    texte_global += " " + texte

                if cms == "Inconnu":
                    texte_page = html_content.lower()
                    for indice, nom in cms_indices.items():
                        if indice in texte_page:
                            cms = nom
                            break

            except Exception as e:
                print(f"Erreur {chemin_html.name} : {e}")
                continue

        try:
            writer.writerow([
                id_site,
                domain,
                date_lisible,
                nom_dossier,
                cms,
                taille_octets_total,
                nb_mots_total,
                nb_images_total,
                nb_boutons_total,
            ])
            print(f"{domain} -> {nb_mots_total} mots -> {nb_images_total} images")

        except Exception as e:
            print(f"Erreur écriture CSV : {e}")

print("Terminé.")