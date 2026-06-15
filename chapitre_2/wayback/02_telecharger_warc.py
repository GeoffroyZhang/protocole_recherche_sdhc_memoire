"""
COLLECTE D'ARCHIVES WEB : WARC + PLAYWRIGHT + MÉTRIQUES       

Pour chaque URL du corpus, ce script :                                      
    1. Interroge l'API CDX pour lister tous les snapshots disponibles         
    2. Télécharge le fichier WARC brut (HTML source + CSS + JS + images)      
    3. Extrait depuis le WARC : HTML source, headers HTTP, encodage, MD5      
    4. Charge le snapshot dans Playwright : screenshot + HTML rendu           
     + métriques inaccessibles hors navigateur (performance, DOM léger)    
    5. Sauvegarde : WARC, HTML rendu, HTML source, screenshot PNG, JSON       

  Ce script ne calcule PAS : nb_images, nb_liens, nb_mots, CMS,              
  réseaux sociaux, ces métriques sont gérées par le script métriques.       

"""
# Import des librairies
import json
import time
import hashlib
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from warcio.archiveiterator import ArchiveIterator


# Dossier de sortie : tous les fichiers seront créés dans ce répertoire
DOSSIER_SORTIE = Path(r"CHEMIN_A_DEFINIR")

# Plage temporelle des snapshots à collecter (format : AAAAMMJJ)
DATE_DEBUT = "20050101"
DATE_FIN   = "20260324"

# Délai (en secondes) entre chaque snapshot pour ne pas surcharger les serveurs
# de la Wayback Machine et éviter d'être bloqué (rate-limiting)
DELAI_ENTRE_SNAPSHOTS = 5

# Timeout HTTP (en secondes) pour les requêtes classiques (CDX API, wget)
TIMEOUT_HTTP = 30

# Timeouts Playwright (en millisecondes) pour le chargement des pages
TIMEOUT_NAVIGATION = 90_000   # 90s max pour qu'une page commence à charger
TIMEOUT_RESEAU     = 15_000   # 15s max d'attente "réseau calme" (networkidle)

# Résolution du navigateur Playwright — fixée pour la reproductibilité
# des screenshots (même rendu à chaque lancement)
VIEWPORT = {"width": 1280, "height": 800}

# URL de l'API CDX de la Wayback Machine
WAYBACK_CDX_API = "https://web.archive.org/cdx/search/cdx"

# User-Agent : on se présente comme un navigateur Firefox normal
# pour éviter d'être bloqué par certains pare-feux
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"
}

# Liste des sites à archiver
URLS = [
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

#  SYSTÈME DE LOGS
#  On configure deux sorties simultanées :
#    - La console (pour suivre l'avancement en direct)
#    - Un fichier collecte.log (pour conserver une trace persistante)
#  En cas d'arrêt brutal du script, toutes les erreurs sont conservées dans
#  le fichier log et permettent de reprendre sans chercher ce qui a échoué.


def configurer_logs(dossier_sortie: Path) -> logging.Logger:
    logger = logging.getLogger("collecte")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")

    # Handler console : affiche les messages INFO et supérieurs
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # Handler fichier : conserve aussi les messages DEBUG (plus verbeux)
    # append = on ne réécrase pas les logs des sessions précédentes
    fichier = logging.FileHandler(dossier_sortie / "collecte.log", encoding="utf-8")
    fichier.setLevel(logging.DEBUG)
    fichier.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(fichier)
    return logger


#  SESSION HTTP AVEC RETRY
#  Quand la Wayback Machine répond avec une erreur temporaire (429 = trop de
#  requêtes, 503 = serveur surchargé), on relance automatiquement la requête
#  en attendant de plus en plus longtemps entre chaque tentative (backoff).
#  Ex : 1ère erreur → attend 2s, 2ème → 4s, 3ème → 8s...

def creer_session_http() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def extraire_domaine(url: str) -> str:
    """
    Extrait le nom de domaine d'une URL pour nommer le dossier de sortie.
    On retire le 'www.' pour uniformiser.
    Ex : https://www.lajcf.fr/page  →  lajcf.fr
    """
    domaine = urlparse(url).netloc
    return domaine[4:] if domaine.startswith("www.") else domaine


def nom_base_fichier(timestamp: str) -> str:
    """
    Construit le préfixe commun à tous les fichiers d'un snapshot.
    Ex : '20120304120000'  →  '20120304_120000'
    Tous les fichiers d'un même snapshot partagent ce préfixe :
      20120304_120000.warc.gz
      20120304_120000.png
      20120304_120000_rendu.html
      20120304_120000_source.html
      20120304_120000_meta.json
    """
    return f"{timestamp[:8]}_{timestamp[8:]}"



#  ÉTAPE 1. API CDX : LISTE DES SNAPSHOTS
#
#  L'API CDX est l'index de la Wayback Machine. Elle retourne la liste de
#  toutes les captures disponibles pour une URL donnée.
#
#  Filtres appliqués :
#    - statuscode:200  → seulement les pages qui ont répondu normalement
#    - collapse=digest → si deux captures ont un contenu identique (même hash),
#                        on n'en garde qu'une pour éviter les doublons
#    - from / to → plage temporelle définie en configuration

def recuperer_snapshots(url: str, session: requests.Session) -> list[str]:
    """
    Retourne la liste des timestamps des snapshots disponibles.
    Ex : ['20120304120000', '20150801093000', '20190612141500', ...]
    """
    params = {
        "url":      url,
        "output":   "json",
        "filter":   "statuscode:200",
        "collapse": "digest",
        "from":     DATE_DEBUT,
        "to":       DATE_FIN,
        "fl":       "timestamp",   # on ne demande que la colonne timestamp
    }
    reponse = session.get(WAYBACK_CDX_API, params=params, headers=HEADERS, timeout=TIMEOUT_HTTP)
    reponse.raise_for_status()
    donnees = reponse.json()

    # La 1ère ligne est l'en-tête ["timestamp"], on la saute avec [1:]
    if len(donnees) <= 1:
        return []

    return [ligne[0] for ligne in donnees[1:]]


#  ÉTAPE 2. TÉLÉCHARGEMENT DU WARC
#
#  On télécharge le snapshot via wget avec le flag "id_" dans l'URL.
#
#  Pourquoi "id_" ?
#    URL normale  : https://web.archive.org/web/20120304120000/https://example.com
#    → La Wayback Machine injecte sa propre barre de navigation + des scripts
#      de réécriture des liens. Le contenu est modifié.
#
#    URL avec id_ : https://web.archive.org/web/20120304120000id_/https://example.com
#    → On obtient la réponse HTTP d'origine, sans aucune modification.
#      C'est le seul moyen d'avoir le contenu dans son état archivé original.
#
#  warc-file : crée un fichier .warc.gz contenant la requête HTTP ET la
#               réponse complète (headers + body). Standard ISO 28500.
#
#  page-requisites : télécharge aussi les ressources liées dans la page
#                      (CSS, JS, images, fonts) pour un WARC complet et
#                      rejouable hors-ligne via pywb.

def telecharger_warc(url: str, timestamp: str, dossier_site: Path, nom_base: str) -> bool:
    """
    Télécharge le snapshot en WARC brut via wget.
    Retourne True si le téléchargement a eu lieu, False si le fichier existait.
    """
    chemin_warc = dossier_site / f"{nom_base}.warc.gz"
    if chemin_warc.exists():
        return False   # déjà téléchargé lors d'une session précédente

    url_brute = f"https://web.archive.org/web/{timestamp}id_/{url}"

    commande = [
        "wget",
        "--warc-file", str(dossier_site / nom_base),  # → nom_base.warc.gz
        "--page-requisites",          # télécharge CSS, JS, images référencés
        "--span-hosts",               # suit les ressources sur d'autres domaines (CDN, etc.)
        "--no-directories",           # ne crée pas d'arborescence locale de fichiers
        "--delete-after",             # supprime les fichiers téléchargés après
                                      # (on ne garde que le WARC, pas les fichiers bruts)
        "--quiet",
        "-e", "robots=off",           # ignore robots.txt (contexte de recherche académique)
        "--timeout", str(TIMEOUT_HTTP),
        "--user-agent", HEADERS["User-Agent"],
        url_brute
    ]

    # check=False : on ne lève pas d'exception si wget retourne un code d'erreur
    # (certaines pages ont des ressources manquantes mais le WARC est quand même créé)
    subprocess.run(commande, capture_output=True, text=True, check=False)
    return chemin_warc.exists()


#  ÉTAPE 3. EXTRACTION DEPUIS LE WARC
#
#  On lit le WARC pour en extraire ce qu'aucun autre script ne peut fournir :
#  les headers HTTP bruts du serveur et l'encodage de la page.
#
#  Un fichier WARC contient des "records" (enregistrements) de différents types :
#    - "warcinfo"  : métadonnées générales du fichier WARC
#    - "request"   : la requête HTTP envoyée par wget
#    - "response"  : la réponse HTTP reçue (headers + body) ← ce qu'on veut
#    - "resource"  : ressource binaire (image, font...)
#
#  Les headers HTTP révèlent des informations invisibles dans le HTML :
#  serveur web (Apache, Nginx), technologie backend (PHP, Python),
#  version du CMS, politique de cache, etc.
#
#  Note : on ne reextrait PAS le texte ici — c'est le rôle du script métriques
#  avec Trafilatura, qui fait ça mieux que BeautifulSoup.

def extraire_depuis_warc(chemin_warc: Path, dossier_site: Path, nom_base: str) -> dict:
    """
    Lit le WARC et extrait :
      - Les headers HTTP de la réponse du serveur (Server, X-Powered-By, etc.)
      - Le HTML source brut sauvegardé dans _source.html
      - L'encodage détecté (UTF-8, GB2312, GBK... important pour le chinois)
      - Un hash MD5 du contenu (pour détecter des doublons résiduels)

    Retourne un dictionnaire utilisé dans les métadonnées JSON.
    """
    metriques_warc = {
        "headers_http":     {},
        "encoding_detecte": None,
        "md5_html_source":  None,
    }

    if not chemin_warc.exists():
        return metriques_warc

    with open(chemin_warc, "rb") as f:
        for record in ArchiveIterator(f):

            # On ne traite que les réponses HTTP
            if record.rec_type != "response":
                continue

            content_type = record.http_headers.get_header("Content-Type", "")

            # On ne traite que les réponses HTML (pas les CSS, images, JS...)
            if "text/html" not in content_type:
                continue

            # Headers HTTP bruts du serveur
            metriques_warc["headers_http"] = {
                cle: valeur for cle, valeur in record.http_headers.headers
            }

            # Détection de l'encodage — crucial pour les sites en chinois
            # qui utilisent parfois GB2312 ou GBK au lieu de UTF-8
            encoding = "utf-8"
            if "charset=" in content_type:
                encoding = content_type.split("charset=")[-1].strip().split(";")[0]
            metriques_warc["encoding_detecte"] = encoding

            # Lecture du corps brut de la réponse
            contenu_bytes = record.content_stream().read()

            # Hash MD5 : empreinte unique du contenu brut
            # Permet de détecter a posteriori les doublons que collapse=digest
            # aurait manqués (même HTML mais ressources externes différentes)
            metriques_warc["md5_html_source"] = hashlib.md5(contenu_bytes).hexdigest()

            # Sauvegarde du HTML source propre (sans aucune injection WM)
            # C'est ce fichier que le script métriques et le script texte liront
            (dossier_site / f"{nom_base}_source.html").write_bytes(contenu_bytes)

            # On s'arrête au premier record HTML = la page principale
            break

    return metriques_warc


#  ÉTAPE 4. PLAYWRIGHT : RENDU VISUEL ET MÉTRIQUES NAVIGATEUR
#
#  Le WARC contient la réponse brute du serveur. Playwright va plus loin :
#  il charge la page comme un vrai navigateur, exécute le JavaScript,
#  applique le CSS et charge les ressources dynamiques.
#
#  Ce que seul Playwright peut fournir (invisible dans le HTML statique) :
#    - Le screenshot pleine page (rendu visuel exact)
#    - Le HTML final après exécution du JS
#    - Les temps de chargement (Web Performance API, mesurés en direct)
#    - Les domaines tiers chargés dynamiquement (analytics, CDN, etc.)
#    - La présence d'un viewport responsive (meta viewport)
#    - La langue déclarée dans le DOM (<html lang="fr">)
#
#  Note : nb_images, nb_liens, nb_formulaires sont intentionnellement absents
#  → ils sont calculés par le script métriques sur le HTML statique.


def attendre_chargement(page) -> None:
    """
    Stratégie de chargement en 2 étapes :
    1. networkidle : attend que le navigateur n'ait plus de requêtes réseau
       en cours depuis 500ms → signal que tout (images, CSS, JS) est chargé.
    2. Fallback : si networkidle expire (page trop lente ou ressources bloquées),
       on attend 8 secondes fixes comme filet de sécurité.
    3. Pause finale de 2s pour les animations JS tardives (lazy-load, sliders).
    """
    try:
        page.wait_for_load_state("networkidle", timeout=TIMEOUT_RESEAU)
    except PlaywrightTimeoutError:
        time.sleep(8)
    page.wait_for_timeout(2_000)


def capturer_rendu(page, url: str, timestamp: str, dossier_site: Path, nom_base: str) -> dict:
    """
    Charge le snapshot Wayback Machine dans Playwright.
    Sauvegarde le HTML rendu et le screenshot PNG.
    Retourne les métriques accessibles uniquement via un navigateur.
    """
    url_snapshot = f"https://web.archive.org/web/{timestamp}/{url}"

    metriques_playwright = {
        "url_snapshot":      url_snapshot,
        "titre":             None,
        "statut_http":       None,
        "performance":       {},
        "dom":               {},
        "erreur_playwright": None,
    }

    try:
        reponse = page.goto(
            url_snapshot,
            timeout=TIMEOUT_NAVIGATION,
            wait_until="domcontentloaded"
            # domcontentloaded = on attend que le HTML de base soit parsé,
            # puis on gère nous-mêmes l'attente des ressources dynamiques.
        )
        attendre_chargement(page)

        # Suppression de la bannière Wayback Machine 
        # La WM injecte une barre de navigation dans chaque page archivée.
        # On la supprime avant le screenshot pour avoir le rendu original.
        page.evaluate("""
            ['#wm-ipp-base', '#wm-ipp', '#wm-ipp-print'].forEach(sel => {
                const el = document.querySelector(sel);
                if (el) el.remove();
            });
        """)

        # Métriques de performance (Web Performance API)
        # Ces données ne sont accessibles qu'au moment du chargement dans un
        # navigateur — impossibles à extraire a posteriori depuis le HTML ou le WARC.
        performance = page.evaluate("""() => {
            const nav = performance.getEntriesByType('navigation')[0];
            const res = performance.getEntriesByType('resource');
            return {
                dom_content_loaded_ms: Math.round(nav?.domContentLoadedEventEnd ?? 0),
                load_complete_ms:      Math.round(nav?.loadEventEnd ?? 0),
                nb_ressources_total:   res.length,
                nb_scripts: res.filter(r => r.initiatorType === 'script').length,
                nb_styles:  res.filter(r => r.initiatorType === 'link').length,
                domaines_tiers: [...new Set(
                    res.map(r => { try { return new URL(r.name).hostname } catch { return '' } })
                       .filter(h => h && !h.includes(location.hostname))
                )]
            };
        }""")

        # Métriques DOM légères 
        # Uniquement ce que le script métriques ne calcule pas déjà.
        dom = page.evaluate("""() => ({
            langue:         document.documentElement.lang || null,
            has_responsive: !!document.querySelector('meta[name="viewport"]'),
            has_schema_org: !!document.querySelector('[itemtype*="schema.org"]'),
            nb_iframes:     document.querySelectorAll('iframe').length,
        })""")

        titre  = page.title()
        statut = reponse.status if reponse else None

        # Sauvegarde du HTML rendu (après exécution JS)
        html_rendu = page.content()
        (dossier_site / f"{nom_base}_rendu.html").write_text(html_rendu, encoding="utf-8")

        # Screenshot pleine page
        # full_page=True : Playwright déroule toute la page pour tout capturer
        page.screenshot(
            path=str(dossier_site / f"{nom_base}.png"),
            full_page=True
        )

        metriques_playwright.update({
            "titre":       titre,
            "statut_http": statut,
            "performance": performance,
            "dom":         dom,
        })

    except PlaywrightTimeoutError as e:
        metriques_playwright["erreur_playwright"] = f"Timeout : {e}"
    except Exception as e:
        metriques_playwright["erreur_playwright"] = str(e)

    return metriques_playwright


#  ÉTAPE 5. SAUVEGARDE DES MÉTADONNÉES
#
#  On regroupe toutes les informations collectées dans un seul fichier JSON.
#  Ce fichier est la "carte d'identité" du snapshot. Il contient uniquement
#  ce que les autres scripts du pipeline ne calculent pas :
#    - Identification (url, domaine, timestamp, dates)
#    - Données navigateur (titre, statut, performance, DOM léger)
#    - Données WARC (headers HTTP serveur, encodage, hash MD5)
#    - Inventaire des fichiers produits avec leurs tailles
#
#  Le JSON sert aussi de point d'entrée pour le script métriques :
#  meta.get("url_snapshot"), meta.get("titre"), meta.get("date") etc.

def sauvegarder_metadonnees(
    url: str,
    domaine: str,
    timestamp: str,
    dossier_site: Path,
    nom_base: str,
    metriques_playwright: dict,
    metriques_warc: dict
) -> None:
    """Crée le fichier JSON de métadonnées fusionnées pour un snapshot."""

    def taille(nom: str) -> int:
        """Retourne la taille en octets d'un fichier, 0 s'il n'existe pas."""
        p = dossier_site / nom
        return p.stat().st_size if p.exists() else 0

    metadonnees = {
        # Identification 
        "url":           url,
        "domaine":       domaine,
        "timestamp":     timestamp,
        "date":          f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
        "heure":         f"{timestamp[8:10]}:{timestamp[10:12]}:{timestamp[12:14]}",
        "date_collecte": datetime.now().isoformat(),

        #Données Playwright 
        "url_snapshot":      metriques_playwright.get("url_snapshot"),
        "titre":             metriques_playwright.get("titre"),
        "statut_http":       metriques_playwright.get("statut_http"),
        "performance":       metriques_playwright.get("performance", {}),
        "dom":               metriques_playwright.get("dom", {}),
        "erreur_playwright": metriques_playwright.get("erreur_playwright"),

        # Données WARC 
        "headers_http_serveur": metriques_warc.get("headers_http", {}),
        "encoding_detecte":     metriques_warc.get("encoding_detecte"),
        "md5_html_source":      metriques_warc.get("md5_html_source"),

        # Inventaire des fichiers produits 
        "fichiers": {
            "warc_gz":     f"{nom_base}.warc.gz",
            "screenshot":  f"{nom_base}.png",
            "html_rendu":  f"{nom_base}_rendu.html",
            "html_source": f"{nom_base}_source.html",
        },
        "tailles_fichiers_octets": {
            "warc_gz":     taille(f"{nom_base}.warc.gz"),
            "screenshot":  taille(f"{nom_base}.png"),
            "html_rendu":  taille(f"{nom_base}_rendu.html"),
            "html_source": taille(f"{nom_base}_source.html"),
        }
    }

    # ensure_ascii=False : préserve les caractères chinois et accentués
    (dossier_site / f"{nom_base}_meta.json").write_text(
        json.dumps(metadonnees, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )




def main():
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    logger = configurer_logs(DOSSIER_SORTIE)
    session_http = creer_session_http()

    nb_sites = len(URLS)
    logger.info(f"Démarrage : {nb_sites} sites à traiter")

    with sync_playwright() as pw:
        navigateur = pw.chromium.launch(headless=True)

        for idx_site, url in enumerate(URLS, start=1):
            domaine = extraire_domaine(url)
            logger.info(f"[{idx_site}/{nb_sites}] {domaine}")

            dossier_site = DOSSIER_SORTIE / domaine
            dossier_site.mkdir(parents=True, exist_ok=True)

            # Récupération des snapshots disponibles 
            try:
                snapshots = recuperer_snapshots(url, session_http)
            except Exception as e:
                logger.error(f"{domaine} : CDX échoué : {e}")
                continue

            if not snapshots:
                logger.info(f"{domaine} : aucun snapshot trouvé")
                continue

            logger.info(f"{domaine} : {len(snapshots)} snapshots à traiter")

            # Contexte navigateur isolé par site
            # Un contexte = profil navigateur indépendant (cookies, cache, storage).
            # Isoler par site évite toute contamination entre domaines.
            contexte = navigateur.new_context(viewport=VIEWPORT)
            page = contexte.new_page()
            compteur_nouveaux = 0

            for timestamp in snapshots:
                nom_base = nom_base_fichier(timestamp)
                date_lisible = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"

                # Reprise sur interruption 
                # Le JSON de métadonnées est le dernier fichier écrit.
                # S'il existe, le snapshot est complet — on le saute.
                if (dossier_site / f"{nom_base}_meta.json").exists():
                    logger.debug(f"{domaine} → {date_lisible} déjà traité, ignoré")
                    continue

                logger.info(f"{domaine} : {date_lisible}")

                # Étape 2 : Téléchargement WARC 
                try:
                    telecharger_warc(url, timestamp, dossier_site, nom_base)
                except Exception as e:
                    logger.error(f"{domaine} / {date_lisible} / wget : {e}")

                # Étape 3 : Extraction depuis le WARC
                chemin_warc = dossier_site / f"{nom_base}.warc.gz"
                metriques_warc = extraire_depuis_warc(chemin_warc, dossier_site, nom_base)

                # Étape 4 : Rendu Playwright 
                metriques_playwright = capturer_rendu(page, url, timestamp, dossier_site, nom_base)

                if metriques_playwright.get("erreur_playwright"):
                    logger.warning(
                        f"{domaine} : {date_lisible} "
                        f"Playwright : {metriques_playwright['erreur_playwright']}"
                    )

                # Étape 5 : Sauvegarde des métadonnées
                sauvegarder_metadonnees(
                    url, domaine, timestamp,
                    dossier_site, nom_base,
                    metriques_playwright, metriques_warc
                )

                compteur_nouveaux += 1
                time.sleep(DELAI_ENTRE_SNAPSHOTS)

            page.close()
            contexte.close()
            logger.info(f"{domaine}: {compteur_nouveaux} nouveaux snapshots collectés")

        navigateur.close()

    logger.info("Collecte terminée.")


if __name__ == "__main__":
    main()