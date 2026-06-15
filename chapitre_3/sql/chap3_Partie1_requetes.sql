### Une première cartographie synchronique du web associatif ###

#--------------------------------------# 
# Pour une géographie de l'histoire
#--------------------------------------#
SELECT COUNT(id_association) AS nb_associations, asso_commune AS commune 
FROM association AS A 
GROUP BY commune;
