# Communautés associatives chinoises sur le Web
## Pour une histoire numérique des Chinois d'outre-mer en France entre 2006 et 2026
### Geoffroy Zhang

**Mémoire de recherche de master 1 SDHC préparé sous la direction de M. le professeur Pierre Singaravélou**

Ce dépôt contient l'ensemble des scripts mobilisés dans le cadre du protocole de recherche du mémoire. Il est organisé selon la structure des chapitres afin de permettre à tout lecteur de retrouver facilement les scripts évoqués dans le corps du texte.

---

## Structure du dépôt

```
protocole_recherche/
│
├── README.md
├── requirements.txt # Dépendances Python
├── requirements_R.txt # Dépendances R
├── corpus_urls.txt # Liste des 46 URL composant le corpus
│
├── chapitre_1/ # Prospection et constitution du corpus
│   ├── rna_nettoyage.py
│   ├── 01_wayback_bornes_chronologiques.py
│   └── R/
│       └── 02_visualisations_bornes_chronologiques.R
│
├── chapitre_2/                   # Protocole de stabilisation du corpus
│   ├── wayback/
│   │   ├── 01_scraping_wayback_accueil.py
│   │   └── 02_telecharger_warc.py
│   ├── extraction/
│   │   ├── 01_wayback_extraction_metriques.py
│   │   └── 01_httrack_extraction_metriques.py
│   ├── base_de_donnees/
│   │   └── exemple_import_bdd.py
│   ├── mcd/
│   │   └── MCD_BDD_ASSOCIATION.pdf
│   └── sql/
│       └── schema.sql
│
└── chapitre_3/                   # Analyse synchronique
    ├── 01_geocodage_association.py
    ├── R/
    │   ├── asso_public_cible.R
    │   ├── associations_par_decennie.R
    │   ├── nb_cms_sites.R
    │   ├── nb_langues.R
    │   ├── occurence_par_commune.R
    │   ├── repartition_demarche.R
    │   └── services_proposes.R
    └── sql/
        ├── chap3_Partie1_requetes.sql
        └── chap3_Partie2_requetes.sql
```

---

## Corpus

Le fichier `corpus_urls.txt` à la racine du dépôt contient la liste des 46 URL composant le corpus de sites web associatifs. Ce fichier constitue le point d'entrée de l'ensemble des scripts du protocole. Il est passé en entrée de la majorité des scripts Python du chapitre 1 et du chapitre 2.

---

## Description des scripts

### Chapitre 1 — Prospection et constitution du corpus

**`rna_nettoyage.py`**
Nettoyage du jeu de données du Répertoire National des Associations (RNA) afin d'identifier les associations chinoises disposant d'un site web. Applique un filtre par mots-clés sur les champs `titre` et `objet` des associations.

**`01_wayback_bornes_chronologiques.py`**
Interroge l'API CDX de la Wayback Machine pour chaque URL du corpus afin de collecter le nombre de snapshots valides, la date du premier snapshot et la date du dernier snapshot. Ces données délimitent les bornes chronologiques du corpus.

**`R/02_visualisations_bornes_chronologiques.R`**
Scripts de visualisation des bornes chronologiques, du nombre de snapshots par URL et de leur distribution statistique (boxplot). Données en entrée : CSV produit par `01_wayback_bornes_chronologiques.py`.

---

### Chapitre 2 — Protocole de stabilisation du corpus

**`wayback/01_scraping_wayback_accueil.py`**
Script principal de collecte des archives visuelles depuis la Wayback Machine. Pour chaque URL du corpus, interroge l'API CDX, charge chaque snapshot dans un navigateur Chromium via Playwright, et sauvegarde trois fichiers par snapshot : le HTML rendu, une capture d'écran pleine page (PNG) et un fichier de métadonnées (JSON).

**`wayback/02_telecharger_warc.py`**
Télécharge le fichier WARC original de chaque snapshot déjà collecté, à partir des timestamps stockés dans les fichiers JSON de métadonnées. Permet la préservation à long terme des archives. À exécuter après `01_scraping_wayback_accueil.py`.

**`extraction/01_wayback_extraction_metriques.py`**
Extrait les métriques techniques de chaque archive HTML collectée par le script de collecte Wayback : nombre de mots (via Trafilatura), nombre d'images, de boutons, de liens internes et externes, présence de réseaux socionumériques, détection du SGC. Produit un CSV destiné à l'import dans la base de données.

**`extraction/01_httrack_extraction_metriques.py`**
Extrait les mêmes métriques depuis les archives HTTrack. Agrège les données de l'ensemble des pages d'un site pour produire une ligne par dispositif dans le CSV de sortie.

**`base_de_donnees/exemple_import_bdd.py`**
Script d'exemple pour l'import d'un fichier CSV dans la base de données MySQL via pandas et SQLAlchemy.

**`mcd/MCD_BDD_ASSOCIATION.pdf`**
Schéma entité-relation (EER) de la base de données, modélisé via MySQL Workbench. Il présente l'ensemble des tables, leurs attributs et leurs relations.

**`sql/schema.sql`**
Schéma SQL de la base de données relationnelle permettant sa recréation.

---

### Chapitre 3 — Analyse synchronique

**`01_geocodage_association.py`**
Géocode les adresses des associations à partir d'un CSV exporté de la base de données. Utilise l'API Nominatim (OpenStreetMap) via geopy pour transformer les adresses en coordonnées GPS. Le fichier produit est importé dans QGIS pour la cartographie.

**`R/`**
Scripts de visualisation des caractéristiques du corpus : répartition par commune, par décennie de création, par SGC, par langue, par démarche, par service proposé et par public ciblé. Données en entrée : CSV exportés depuis la base de données via les requêtes SQL.

**`sql/`**
Requêtes SQL utilisées pour l'extraction des données de la base de données en vue des analyses et visualisations du chapitre 3.

---

## Prérequis

### Python
```bash
pip install -r requirements.txt
playwright install chromium
```

### R
Les librairies R requises sont listées dans `requirements_R.txt`. Installation depuis R :
```r
install.packages(c("ggplot2", "tidyverse", "modelsummary"))
```

### Base de données
- MySQL pour l'hébergement de la base de données
- MySQL Workbench pour la modélisation et l'exécution des requêtes
- LibreOffice Base pour la saisie manuelle via formulaires

### HTTrack
Le logiciel HTTrack est disponible sur : https://www.httrack.com

### IRaMuTeQ
Les analyses textométriques (CDH, graphe de similitude, AFC) ont été réalisées via le logiciel IRaMuTeQ, disponible sur : https://pratinaud.gitpages.huma-num.fr/iramuteq-website/

---

## Notes importantes

- Les chemins absolus présents dans les scripts sont à adapter à votre propre environnement avant exécution.
- Les données brutes (archives HTML, PNG, WARC, CSV) ne sont pas incluses dans ce dépôt pour des raisons de droits d'auteur et de volume.
- La reproductibilité de l'étape de moissonnage Hyphe n'est pas garantie en raison de la nature évolutive du Web vivant.

---

## Citation

Si vous utilisez ce protocole dans vos travaux, merci de citer :

> Zhang, Geoffroy. *Communautés associatives chinoises sur le Web. Pour une histoire numérique des Chinois d'outre-mer en France entre 2006 et 2026*. Mémoire de recherche SDHC, 2026.
