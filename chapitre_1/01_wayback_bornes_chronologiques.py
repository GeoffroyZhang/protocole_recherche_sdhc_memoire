# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 23:13:23 2026

@author: Zhang
"""

"""
Objectif : Interroger l'API de la Wayback Machine afin de collecter des informations sur les sites
que sont le nombre de snapshots valides (status code de 200) ; la date du premier snapshot ; et la 
date du dernier snapshot afin de délimiter les limites temporelles de mon corpus. 
Ce protocole s'appliquant seulement aux pages d'accueil des différents sites (urls) puisque la profondeur
d'archivage varie selon les sites, donc il n'est pas pertinent d'extraire tout le site en raison des
sauts temporels d'un lien à un autre au sein de la même entité web.
"""

import requests
import csv
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Interrogation de l'API
API_Wayback = "https://web.archive.org/cdx/search/cdx"
dossier_sortie = r"CHEMIN_A_DEFINIR"

# Paramètres 
deley_requests = 1  # secondes
max_tentatives = 5
timeout = 20


def create_session():
    session = requests.Session()
    retries = Retry(
        total=max_tentatives,
        backoff_factor=1,  # délai progressif entre tentatives
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session



def get_wayback_info(session, url):
    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp",
        "filter": "statuscode:200"
    }

    try:
        response = session.get(API_Wayback, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        if len(data) <= 1:
            return 0, None, None

        timestamps = [row[0] for row in data[1:]]
        count = len(timestamps)

        first = min(timestamps)
        last = max(timestamps)

        first_date = datetime.strptime(first, "%Y%m%d%H%M%S")
        last_date = datetime.strptime(last, "%Y%m%d%H%M%S")

        return count, first_date, last_date

    except Exception as e:
        print(f"Erreur pour {url}: {e}")
        return 0, None, None

# Liste des Urls
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

session = create_session()

with open(dossier_sortie, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["URL", "Nombre_snapshots", "Premiere_archive", "Derniere_archive"])

    for url in urls:
        print(f"Analyse de {url}...")
        count, first, last = get_wayback_info(session, url)

        writer.writerow([
            url,
            count,
            first.strftime("%Y-%m-%d %H:%M:%S") if first else "",
            last.strftime("%Y-%m-%d %H:%M:%S") if last else ""
        ])

        time.sleep(deley_requests)

print("Terminé.")