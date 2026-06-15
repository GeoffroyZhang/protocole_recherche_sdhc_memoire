"""
Collecte d'archives visuelles depuis la Wayback Machine.

Pour chaque URL du corpus, ce script :
  1. Récupère la liste de tous les snapshots disponibles (API CDX)
  2. Pour chaque snapshot, charge la page dans un navigateur (Playwright)
  3. Attend que la page soit vraiment chargée (images, CSS, JS)
  4. Sauvegarde : le HTML rendu, un screenshot pleine page, et les métadonnées JSON
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



dossier_sortie = Path(r"CHEMIN_A_DEFINIR")

date_debut = "20050101"
date_fin   = "20260324"

delai_entre_snapshots = 4        # secondes d'attente entre chaque snapshot (respecter l'API)
timeout_http          = 30       # secondes max pour les requêtes HTTP classiques
timeout_navigation    = 90_000   # ms : temps max pour qu'une page commence à répondre
timeout_reseau        = 15_000   # ms : on attend que le réseau se calme (plus de requêtes en cours)

wayback_cdx_api = "https://web.archive.org/cdx/search/cdx"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"
}

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
    "https://www.affclyon.org/fr/",
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
    "https://www.huayuan.fr/site/index.php?",
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
    "https://amicaleteochew.fr/zh/",
    "http://www.frhuaqiao.com",
    "https://www.acrf.paris",
    "https://www.uchrafr.com",
    "http://www.adefc.org",
    "https://liaoning-france.com",
    "https://calligraphieetculturechinoise.fr",
    "https://www.acwf.fr",
    "http://jeunechinoisdeurope.com",
    "http://www.huiji.org",
]

def creer_session_http():
    """
    Crée une session HTTP avec retry automatique.
    En cas d'erreur serveur (500, 503...) ou de rate-limit (429),
    la requête sera relancée automatiquement jusqu'à 5 fois.
    """
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,                          # attend 2s, 4s, 8s... entre les essais
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def extraire_domaine(url):
    """
    Extrait le nom de domaine d'une URL, sans le 'www.'.
    Ex : https://www.lajcf.fr  ->  lajcf.fr
    """
    domaine = urlparse(url).netloc
    if domaine.startswith("www."):
        domaine = domaine[4:]
    return domaine


def recuperer_snapshots(url, session):
    """
    Interroge l'API CDX de la Wayback Machine pour obtenir
    la liste des snapshots disponibles pour une URL.

    Filtres appliqués :
      - Seulement les pages avec un code HTTP 200 (page trouvée)
      - Pas de doublons (collapse=digest : on ignore les snapshots identiques)
      - Seulement entre date_debut et date_fin

    Retourne une liste de timestamps, ex : ['20120304120000', '20150801093000', ...]
    """
    params = {
        "url":      url,
        "output":   "json",
        "filter":   "statuscode:200",
        "collapse": "digest",
        "from":     date_debut,
        "to":       date_fin,
    }

    reponse = session.get(wayback_cdx_api, params=params, headers=headers, timeout=timeout_http)
    reponse.raise_for_status()
    donnees = reponse.json()

    # La première ligne est l'en-tête (noms des colonnes), on la saute
    if len(donnees) <= 1:
        return []

    # Colonne index 1 = timestamp
    return [ligne[1] for ligne in donnees[1:]]



def attendre_chargement_complet(page):
    """
    Stratégie en 3 étapes pour s'assurer que la page est vraiment chargée :

    Etape 1 — networkidle : attend que le navigateur n'ait plus de requêtes réseau
               en cours depuis 500ms. C'est le signal le plus fiable que tout
               (images, CSS, JS) a fini de se charger.

    Etape 2 — Si networkidle échoue (page trop lente ou ressources bloquées),
               on se replie sur un délai fixe de 8 secondes. C'est le filet de sécurité.

    Etape 3 — On attend encore 2 secondes après le chargement pour laisser
               le temps aux animations JS de se terminer (ex: sliders, lazy-load).
    """
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_reseau)
    except PlaywrightTimeoutError:
        # La page n'est pas devenue "idle" dans le temps imparti.
        # On attend quand même un peu pour maximiser les chances d'avoir une page complète.
        print("    networkidle dépassé, attente de secours de 8s...")
        time.sleep(8)

    # Pause finale pour le JS tardif (lazy-load d'images, animations, etc.)
    page.wait_for_timeout(2_000)


def capturer_snapshot(page, url, domaine, timestamp, dossier_site):
    """
    Charge un snapshot Wayback Machine et sauvegarde 3 fichiers :
      - AAAAMMJJ_HHMMSS.html      -> le HTML tel que rendu par le navigateur
      - AAAAMMJJ_HHMMSS.png       -> screenshot pleine page
      - AAAAMMJJ_HHMMSS_meta.json -> métadonnées (URL, titre, date, taille...)

    Retourne True si le snapshot a été traité, False s'il existait déjà.
    """
    # Nom de base des fichiers : date + heure du snapshot
    nom_base   = f"{timestamp[:8]}_{timestamp[8:]}"
    chemin_png = dossier_site / f"{nom_base}.png"

    # Si le PNG existe déjà -> ce snapshot a déjà été traité, on passe
    if chemin_png.exists():
        return False

    url_snapshot = f"https://web.archive.org/web/{timestamp}/{url}"

    # Chargement de la page
    reponse = page.goto(url_snapshot, timeout=timeout_navigation, wait_until="domcontentloaded")
    # "domcontentloaded" = on attend que le HTML de base soit parsé,
    # puis on gère nous-mêmes l'attente des ressources avec attendre_chargement_complet()

    attendre_chargement_complet(page)

    # Collecte des données
    statut_http  = reponse.status if reponse else None
    titre        = page.title()
    html_rendu   = page.content()

    # Sauvegarde HTML
    (dossier_site / f"{nom_base}.html").write_text(html_rendu, encoding="utf-8")

    # Screenshot pleine page
    # full_page=True : Playwright fait défiler toute la page pour tout capturer
    page.screenshot(path=str(chemin_png), full_page=True)

    # Métadonnées JSON
    metadonnees = {
        "url":                url,
        "domaine":            domaine,
        "timestamp":          timestamp,
        "date":               f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
        "heure":              f"{timestamp[8:10]}:{timestamp[10:12]}:{timestamp[12:14]}",
        "url_snapshot":       url_snapshot,
        "titre":              titre,
        "statut_http":        statut_http,
        "date_collecte":      datetime.now().isoformat(),
        "taille_html_octets": len(html_rendu.encode("utf-8")),
    }
    (dossier_site / f"{nom_base}_meta.json").write_text(
        json.dumps(metadonnees, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    return True




def main():

    dossier_sortie.mkdir(parents=True, exist_ok=True)
    session_http = creer_session_http()

    with sync_playwright() as pw:
        navigateur = pw.chromium.launch(headless=True)
        # Une seule page réutilisée pour tous les snapshots d'un même site.
        # Cela évite d'ouvrir/fermer un onglet à chaque snapshot (plus rapide).
        page = navigateur.new_page()

        for url in urls:
            domaine = extraire_domaine(url)
            print(f"\nSite : {domaine}")

            dossier_site = dossier_sortie / domaine
            dossier_site.mkdir(parents=True, exist_ok=True)

            # Récupération des snapshots disponibles
            try:
                snapshots = recuperer_snapshots(url, session_http)
            except Exception as e:
                print(f"  Impossible de récupérer les snapshots : {e}")
                continue

            if not snapshots:
                print("  Aucun snapshot trouvé pour cette URL.")
                continue

            print(f"  {len(snapshots)} snapshots à traiter")
            compteur = 0

            # Traitement snapshot par snapshot
            for timestamp in snapshots:
                try:
                    traite = capturer_snapshot(page, url, domaine, timestamp, dossier_site)

                    if traite:
                        compteur += 1
                        print(f"  {timestamp[:8]} {timestamp[8:10]}h{timestamp[10:12]}")
                        time.sleep(delai_entre_snapshots)
                    else:
                        print(f"  deja traite : {timestamp[:8]}")

                except Exception as e:
                    print(f"  Erreur sur {timestamp} : {e}")
                    time.sleep(6)

            print(f"Total nouveaux snapshots capturés : {compteur}")

        page.close()
        navigateur.close()


if __name__ == "__main__":
    main()