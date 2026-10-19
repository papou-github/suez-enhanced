# SUEZ Enhanced

Intégration personnalisée Home Assistant pour le portail **Tout sur mon Eau (SUEZ)**, distribuée via HACS.

> Projet communautaire non officiel : l'API SUEZ peut évoluer. Ne communiquez jamais vos identifiants ni vos journaux sans anonymisation.

## Installation via HACS

1. Dans HACS, ouvrez les **dépôts personnalisés** et ajoutez `https://github.com/papou-github/suez-enhanced` comme **Integration**.
2. Téléchargez SUEZ Enhanced et **redémarrez Home Assistant Core** après installation ou mise à jour du code.
3. Dans **Paramètres → Appareils et services**, ajoutez **SUEZ Enhanced** et connectez-vous avec les identifiants du portail SUEZ.
4. Le numéro de compteur est détecté automatiquement.

## Entités

- **Meter index** : index du compteur en m³ (`total_increasing`).
- **Water usage yesterday** : volume de la veille en litres.

L'API est interrogée toutes les **6 heures**.

## Historique du tableau Énergie

L'intégration recherche la série historique existante `suez_water:<compteur>_water_consumption_statistics`, puis y ajoute les journées complètes manquantes. La synchronisation est **activée par défaut** et désactivable dans **Paramètres → Appareils et services → SUEZ Enhanced → Configurer**.

Protections : pas de création d'une nouvelle série si l'ancienne n'existe pas, pas de remplacement des anciens relevés, uniquement les journées consécutives, délai de sécurité de deux jours avant import. La série historique reste en **litres**. L'index du compteur en m³ est une autre entité : **ne l'ajoutez pas comme deuxième source d'eau dans Énergie si la série historique est déjà sélectionnée**, sinon les volumes risquent d'être comptés deux fois.

Avant la première activation de l'écriture dans les statistiques, effectuez une **sauvegarde complète Home Assistant**. Les journaux de diagnostic sont disponibles avec :

```bash
ha core logs | grep -iE 'SUEZ historical continuity|SUEZ statistics continuity'
```

## Mises à jour

Les **données de consommation** se synchronisent automatiquement toutes les six heures. **HACS** peut détecter les nouvelles versions du code, mais leur installation dépend de votre configuration HACS ; un **redémarrage de Home Assistant Core** est nécessaire pour charger les nouveaux modules Python. Pour la sécurité des statistiques, aucune installation ni aucun redémarrage forcé n'est déclenché par cette intégration.

## Développement et validation

Les workflows GitHub Actions exécutent la validation HACS, hassfest et des contrôles Python/JSON à chaque push ou pull request. Les résultats doivent être consultés dans l'onglet **Actions** du dépôt ; leur présence ne signifie pas qu'ils ont déjà réussi.

## Limitations

- API SUEZ non officielle, susceptible de changer.
- Découverte d'un seul compteur par configuration.
- La reprise historique suppose une série créée auparavant par l'intégration SUEZ d'origine ; les nouvelles installations sans historique peuvent utiliser le capteur d'index.
- Les relevés journaliers restent soumis aux délais et éventuelles corrections du portail SUEZ.
