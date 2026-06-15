use bdd_association_site;

##### Composition et caractéristiques des associations #####

#--------------------------------------# 
# Les acteurs associatifs en France 
#--------------------------------------#
# Répartition selon que l'association fait partie de la diaspora chinoise ou non 
SELECT diaspora, COUNT(*) AS nb_associations
FROM association
GROUP BY diaspora
ORDER BY nb_associations DESC;

# Ancienneté des associations 
SELECT date_association, COUNT(*) AS nb_associations
FROM association
GROUP BY date_association
ORDER BY date_association;

# Nombre d'associations par décennie 
SELECT 
    CASE
        WHEN date_association IS NULL THEN 'Non renseigné'
        ELSE CONCAT(FLOOR(date_association / 10) * 10, 's')
    END AS decennie,
    COUNT(*) AS nb_associations
FROM association
GROUP BY decennie
ORDER BY decennie;

#--------------------------------------# 
# Des sites web hétérogènes ?  
#--------------------------------------#

# Nombre de sites actifs
SELECT statut, COUNT(*) AS nb_sites
FROM site
GROUP BY statut;

# Les CMS utilisés par les dispositifs 
SELECT cms, COUNT(DISTINCT id_site) AS nb_sites
FROM archive_site
GROUP BY cms
ORDER BY nb_sites DESC;

# La distribution des langues 
SELECT L.code_langue, COUNT(langue_defaut) AS nb_sites
FROM site_langue AS SL
INNER JOIN langue AS L ON SL.id_langue = L.id_langue
GROUP BY L.code_langue
ORDER BY nb_sites DESC;

# Site uniquement dans une langue
SELECT 
    l.code_langue AS langue_unique,
    COUNT(DISTINCT sl.id_site) AS nb_sites
FROM site_langue sl
INNER JOIN langue l ON l.id_langue = sl.id_langue
WHERE sl.id_site IN (
    SELECT id_site
    FROM site_langue
    GROUP BY id_site
    HAVING COUNT(DISTINCT id_langue) = 1
)
AND l.code_langue IN ('fr', 'zh')
GROUP BY l.code_langue;

# Site monolingue ou multilingue
SELECT
    CASE
        WHEN nb_langues = 1 THEN 'Monolingue'
        WHEN nb_langues = 2 THEN 'Bilingue'
        ELSE 'Multilingue (3 langues et plus)'
    END AS type_linguistique,
    COUNT(*) AS nb_sites
FROM (
    SELECT id_site, COUNT(DISTINCT id_langue) AS nb_langues
    FROM site_langue
    GROUP BY id_site
) comptage
GROUP BY type_linguistique
ORDER BY nb_sites DESC;

# Répartition des services proposés 
SELECT s.service, COUNT(ss.id_site) AS nb_sites
FROM service s
INNER JOIN site_service ss ON ss.id_service = s.id_service
GROUP BY s.service
ORDER BY nb_sites DESC;

# Répartition des démarches 
SELECT d.type_demarche, COUNT(sd.id_site) AS nb_sites
FROM demarche d
INNER JOIN site_demarche sd ON sd.id_demarche = d.id_demarche
GROUP BY d.type_demarche
ORDER BY nb_sites DESC;

# Public ciblé
SELECT p.public, p.type_public, COUNT(sc.id_site) AS nb_sites
FROM public p
JOIN site_cible sc ON sc.id_public = p.id_public
GROUP BY p.id_public
ORDER BY nb_sites DESC;

#--------------------------------------# 
# Portrait d'un corpus complexe
#--------------------------------------#

# 1. site et diaspora
SELECT s.id_site, s.site_url, a.diaspora
FROM site s
INNER JOIN association a ON s.id_association = a.id_association;

# 2. site et langue
SELECT sl.id_site, l.code_langue
FROM site_langue sl
INNER JOIN langue l ON sl.id_langue = l.id_langue;

# 3. site et public cible
SELECT sc.id_site, p.public, p.type_public
FROM site_cible sc
JOIN public p ON sc.id_public = p.id_public;

# 4. site et démarche
SELECT sd.id_site, d.type_demarche
FROM site_demarche sd
INNER JOIN demarche d ON sd.id_demarche = d.id_demarche;

# 5. Origine et profil linguistique
SELECT 
    a.diaspora,
    COUNT(CASE WHEN nb_langues = 1 AND code_langue = 'fr' THEN 1 END) AS mono_fr,
    COUNT(CASE WHEN nb_langues = 1 AND code_langue = 'zh' THEN 1 END) AS mono_zh,
    COUNT(CASE WHEN nb_langues = 2 THEN 1 END) AS bilingue,
    COUNT(CASE WHEN nb_langues >= 3 THEN 1 END) AS multilingue
FROM association a
INNER JOIN site s ON a.id_association = s.id_association
INNER JOIN (
    SELECT 
        sl.id_site, 
        COUNT(sl.id_langue) AS nb_langues,
        MAX(l.code_langue) AS code_langue
    FROM site_langue sl
    INNER JOIN langue l ON sl.id_langue = l.id_langue
    GROUP BY sl.id_site
) lang ON s.id_site = lang.id_site
GROUP BY a.diaspora;

# Démarche et présence zh et public chinois
SELECT 
    d.type_demarche,
    COUNT(DISTINCT sd.id_site) AS "nb_sites",
    COUNT(DISTINCT CASE WHEN l.code_langue = 'zh' 
        THEN sd.id_site END) AS avec_zh,
    COUNT(DISTINCT CASE WHEN p.public = 'chinois' 
        THEN sd.id_site END) AS cible_chinois
FROM site_demarche sd
INNER JOIN demarche d ON sd.id_demarche = d.id_demarche
LEFT JOIN site_langue sl ON sd.id_site = sl.id_site
LEFT JOIN langue l ON sl.id_langue = l.id_langue
LEFT JOIN site_cible sc ON sd.id_site = sc.id_site
LEFT JOIN public p ON sc.id_public = p.id_public
GROUP BY d.type_demarche; 