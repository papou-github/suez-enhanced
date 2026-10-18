# SUEZ Enhanced

Intégration personnalisée Home Assistant pour le portail Tout sur mon Eau (SUEZ).

**Version 0.1.0 — expérimentale.** Ne remplacez pas une source existante du tableau de bord Énergie avant validation de l'index et de ses statistiques.

## Installation HACS

Ajoutez `https://github.com/papou-github/suez-enhanced` comme dépôt personnalisé de type **Integration** dans HACS, installez puis redémarrez Home Assistant. Ajoutez **SUEZ Enhanced** dans Paramètres > Appareils et services.

## Capteurs

- **Meter index** : index réel du compteur en m³, `state_class: total_increasing`, destiné au tableau de bord Énergie.
- **Water usage yesterday** : volume du jour précédent en litres, quand disponible.

Le compteur est découvert automatiquement. Rafraîchissement toutes les six heures. L'index provient de la dernière mesure quotidienne disposant d'un index valide sur les 14 derniers jours.

## Limitations

- API SUEZ non officielle, susceptible de changer.
- Une seule découverte automatique de compteur par compte est actuellement prise en charge.
- Les consommations mensuelles/annuelles et le prix de l'eau sont prévus pour une version ultérieure.
- La première publication du capteur d'index ne reconstitue pas automatiquement les statistiques historiques du tableau de bord Énergie.

## Confidentialité

Les identifiants sont stockés dans l'entrée de configuration de Home Assistant. Ne publiez jamais vos journaux contenant des informations personnelles sans les masquer.
