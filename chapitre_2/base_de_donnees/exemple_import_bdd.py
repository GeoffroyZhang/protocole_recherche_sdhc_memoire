"""Script pour l'import des données du CSV sur les métriques dans ma BDD"""

import pandas as pd
from sqlalchemy import create_engine

"""L'import de données via pandas est beaucoup plus efficace car il y a moins de contraintes."""

# Connexion à MySQL
engine = create_engine(
    "mysql+pymysql://root:motDePasse@localhost/bdd_association_site?charset=utf8mb4"
)

# Lecture du CSV
df = pd.read_csv(chemin du fichier .CSV)

# Import dans MySQL
df.to_sql(
    name="nom de la table",
    con=engine,
    if_exists="append",  # ajoute sans écraser
    index=False
)

print("Import terminé !")