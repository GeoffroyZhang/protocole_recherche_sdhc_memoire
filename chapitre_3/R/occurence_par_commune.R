library(ggplot2)

# Chargement des données
df <- read.csv("occurence_par_commune.csv", stringsAsFactors = FALSE)

# Nettoyage : supprimer la ligne NULL et les espaces superflus
df <- df[df$asso_commune != "NULL", ]
df$Communes <- as.integer(df$Communes)

# Tri par nombre d'occurrences décroissant
df <- df[order(df$Communes, decreasing = TRUE), ]
df$asso_commune <- factor(df$asso_commune, levels = df$asso_commune)

# Graphique
p <- ggplot(df, aes(x = asso_commune, y = Communes)) +
  geom_bar(stat = "identity", fill = "#2C6E9E") +
  geom_text(aes(label = Communes), hjust = -0.2, size = 3) +
  coord_flip() +
  labs(
    x = NULL,
    y = "Occurrences"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold", margin = margin(b = 10)),
    panel.grid.major.y = element_blank(),
    panel.grid.minor  = element_blank(),
    axis.text.y       = element_text(size = 9)
  ) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15)))

p

ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/Redaction_memoire/Memoire_Latex/figures/01_Partie/occurrences_par_communes.pdf", width = 10, height = 4, device = cairo_pdf)
ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/Base_de_donnees/bdd_memoire/requetes_sql/data_set_export/occurrences_par_communes.pdf", width = 10, height = 4, device = cairo_pdf)