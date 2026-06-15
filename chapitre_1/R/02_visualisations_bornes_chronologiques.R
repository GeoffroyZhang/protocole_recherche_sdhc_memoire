library(ggplot2)
library(tidyverse)
#install.packages("modelsummary")
library(modelsummary)

df <- read.csv(file = "C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/WaybackMachine/bornes_archives/sources/ArchivesDates.csv", header = TRUE, sep = ",")

head(df)
summary(df$Nombre_snapshots)

df1 <- data.frame(df$Nombre_snapshots)

# Visualisation globale du nombre de snapshots


boxplot_general <- ggplot(
  data = df, 
  mapping = aes(x=Nombre_snapshots, y = ))+
  geom_boxplot(outlier.colour="red", outlier.shape=8, outlier.size=3, fill="lightblue")+
  labs(
    x="Nombre de snapshots",
    y=NULL
  ) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.minor   = element_blank(),
    axis.text.y        = element_blank(),
    axis.ticks.y       = element_blank()
  )

boxplot_general

ggsave("Boxplot_general.pdf", plot = boxplot_general,
       device = cairo_pdf, width = 10, height = 2)
ggsave("Boxplot_general.png", plot = boxplot_general,
       width = 10, height = 2, dpi = 600)


# Visualisation du nombre de snapshots par url

p <- df |>
  mutate(
    url_court = str_remove(URL, "https?://(www\\.)?") |> str_trunc(30)
  ) |>
  arrange(Nombre_snapshots) |>
  mutate(url_court = fct_inorder(url_court)) |>
  ggplot(aes(x = Nombre_snapshots, y = url_court)) +
  geom_col(fill = "#2c7bb6", width = 0.6) +
  geom_text(aes(label = Nombre_snapshots), hjust = -0.3, size = 3.5) +
  scale_x_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(x = "Nombre de snapshots", y = NULL) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    axis.line.y = element_line(colour = "grey40"),
    axis.ticks.y = element_line(colour = "grey40")
  )

p

ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/Redaction_memoire/Memoire_Latex/figures/01_Partie/Nombre_de_snapshots_par_site.pdf",
       plot = p, width = 8, height = 8, device = cairo_pdf)

ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/WaybackMachine/bornes_archives/outputs/Nombre_de_snapshots_par_site.pdf",
       plot = p, width = 8, height = 8, device = cairo_pdf)



# Visualisation des bornes chronologiques des archives web
# Diagramme de Gantt — Première et dernière archive par site


# Packages
library(ggplot2)
library(dplyr)
library(lubridate)
library(scales)

chemin <- "C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/WaybackMachine/bornes_archives/sources/ArchivesDates.csv"

# Chargement
df <- read.csv(chemin, stringsAsFactors = FALSE) |>
  mutate(
    debut = ymd_hms(Premiere_archive),
    fin   = ymd_hms(Derniere_archive),
    label = gsub("https?://(www\\.)?|/.*", "", URL),
    label = reorder(label, as.numeric(fin - debut))
  )

# Bornes globales du corpus
borne_debut <- min(df$debut)
borne_fin   <- max(df$fin)

# Graphique
ggplot(df, aes(y = label)) +
  geom_segment(aes(x = debut, xend = fin, yend = label),
               linewidth = 2.5, lineend = "round", color = "#4393c3") +
  geom_vline(xintercept = as.numeric(borne_debut),
             linetype = "dashed", color = "#d73027", linewidth = 0.5) +
  geom_vline(xintercept = as.numeric(borne_fin),
             linetype = "dashed", color = "#1a9850", linewidth = 0.5) +
  annotate("text", x = borne_debut, y = -1,
           label = paste0("Première archive\n", format(borne_debut, "%d %b %Y")),
           hjust = 0.5, size = 2.8, color = "#d73027") +
  annotate("text", x = borne_fin, y = -1,
           label = paste0("Dernière archive\n", format(borne_fin, "%d %b %Y")),
           hjust = 0.5, size = 2.8, color = "#1a9850")+
  scale_x_datetime(
    breaks = seq(ymd_hms("2005-01-01 00:00:00"), ymd_hms("2026-05-08 00:00:00"), by = "2 years"),
    labels = date_format("%Y"),
    limits = c(ymd_hms("2004-01-01 00:00:00"), ymd_hms("2026-05-08 00:00:00"))
  ) +
  labs(title = "", x = NULL, y = NULL) +
  theme_minimal(base_size = 9) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor   = element_blank(),
    axis.text.y        = element_text(size = 9)
  )

# Export PDF pour LaTeX
ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/WaybackMachine/bornes_archives/outputs/bornes_chronologiques_archives.pdf",
       device = cairo_pdf,
       width = 11, height = 8)

ggsave("C:/Users/Zhang/OneDrive/Bureau/Memoire_SDHC/WaybackMachine/bornes_archives/outputs/bornes_chronologiques_archives.png",
       width = 11, height = 8, dpi = 600)