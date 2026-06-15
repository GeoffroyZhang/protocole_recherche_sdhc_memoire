library(ggplot2)
library(tidyverse)

df <- read.csv("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/Base_de_donnees/bdd_memoire/requetes_sql/data_set_export/services_proposes.csv")

ggplot(df, aes(x = fct_reorder(service, nb_sites), y = nb_sites)) +
  geom_col(fill = "#2c7bb6", width = 0.6) +
  geom_text(aes(label = nb_sites), hjust = -0.3, size = 3.5) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(x = NULL, y = "Nombre de sites") +
  coord_flip() +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    axis.line.y = element_line(colour = "grey40"),
    axis.ticks.y = element_line(colour = "grey40")
  )


ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/Redaction_memoire/Memoire_Latex/figures/01_Partie/services_proposes.pdf", width = 6, height = 3, device = cairo_pdf)
ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/Base_de_donnees/bdd_memoire/requetes_sql/data_set_export/services_proposes.pdf", width = 6, height = 3, device = cairo_pdf)