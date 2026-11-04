# SUEZ Enhanced — Home Assistant HACS water consumption integration

[![Latest release](https://img.shields.io/github/v/release/papou-github/suez-enhanced?label=release)](https://github.com/papou-github/suez-enhanced/releases/latest)
[![License: MIT](https://img.shields.io/github/license/papou-github/suez-enhanced)](LICENSE)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/papou-github/suez-enhanced/hacs.yml?label=HACS)](https://github.com/papou-github/suez-enhanced/actions)

[🇫🇷 Français](#français) · [🇬🇧 English](#english) · [Releases](https://github.com/papou-github/suez-enhanced/releases) · [Issues](https://github.com/papou-github/suez-enhanced/issues)

**SUEZ Enhanced** is an **unofficial custom Home Assistant integration**, installable through **HACS**, for tracking **SUEZ / Tout sur mon Eau** water meter readings, water consumption and Home Assistant **Energy dashboard** history.

**SUEZ Enhanced** est une **intégration communautaire Home Assistant**, installable via **HACS**, pour suivre la consommation d'eau **SUEZ / Tout sur mon Eau**, l'index du compteur, les statistiques du tableau de bord **Énergie** et les estimations de coût.

> **Unofficial / Non officiel :** This project is not affiliated with or endorsed by SUEZ. The underlying API can change. Back up Home Assistant before enabling historical-statistics synchronization. / Projet non affilié à SUEZ. L'API peut évoluer. Sauvegardez Home Assistant avant toute synchronisation historique.

---

## Français

### Fonctionnalités (v0.4.0)

- **Relevés automatiques** du portail SUEZ **Tout sur mon Eau**, actualisés toutes les **6 heures**.
- **Détection automatique du compteur** lors de la configuration.
- **Index du compteur en m³** et **consommation de la veille en litres**.
- **Consommation des 7 derniers jours**, **consommation du mois en cours** et **moyenne quotidienne sur 7 jours**.
- **Estimation du coût mensuel** avec **tarif de l'eau configurable en €/m³**.
- **Continuité de l'historique** du tableau de bord **Énergie** pour les installations utilisant déjà les statistiques SUEZ historiques.
- **Cinq capteurs de diagnostic facultatifs**, désactivés par défaut.
- Interface et documentation en **français et anglais**.

### Installation avec HACS

1. Ouvrez **HACS → Dépôts personnalisés**.
2. Ajoutez `https://github.com/papou-github/suez-enhanced` en choisissant le type **Integration**.
3. Installez **SUEZ Enhanced**, puis **redémarrez Home Assistant Core**.
4. Allez dans **Paramètres → Appareils et services → Ajouter une intégration → SUEZ Enhanced**.
5. Saisissez les identifiants du portail **Tout sur mon Eau (SUEZ)**. Le compteur est détecté automatiquement.

**Prérequis :** Home Assistant **2025.1.0 ou ultérieur**, HACS pour l'installation via les dépôts personnalisés et un compte compatible sur le portail SUEZ.

### Capteurs disponibles

| Capteur | Description |
| --- | --- |
| **Meter index** | Index cumulatif du compteur, en m³ (`total_increasing`) |
| **Water usage yesterday** | Consommation de la veille, en litres, si disponible |
| **Consumption last 7 days** | Consommation consolidée des sept derniers jours, en litres |
| **Consumption this month** | Consommation du mois en cours, en litres |
| **Daily average (7 days)** | Moyenne quotidienne sur sept jours, en litres |
| **Estimated month cost** | Coût mensuel estimé en euros, selon le tarif configuré |

Les cinq capteurs de diagnostic facultatifs renseignent notamment la dernière synchronisation, le dernier relevé, le dernier jour d'historique, les jours en attente et l'état de synchronisation.

### Tableau de bord Énergie : préserver l'historique SUEZ

Si votre installation Home Assistant possède déjà une série de statistiques SUEZ, l'intégration peut **prolonger cette série sous son identifiant d'origine**, par exemple `suez_water:<numéro_de_compteur>_water_consumption_statistics`.

La synchronisation historique est **activée par défaut** et peut être désactivée dans les **options de l'intégration**.

Protections intégrées :
- Aucune création d'une nouvelle série historique en l'absence d'une série compatible existante.
- Aucune réécriture des journées déjà enregistrées.
- Ajout uniquement des journées manquantes consécutives.
- Délai de sécurité de **deux jours** avant import.
- Conservation des statistiques historiques en **litres**.

> **Éviter le double comptage :** si l'ancienne série SUEZ est déjà utilisée comme source d'eau dans le tableau de bord Énergie, **n'ajoutez pas aussi Meter index** comme deuxième source d'eau du réseau.

Pour une nouvelle installation **sans ancienne série SUEZ**, le capteur **Meter index** en m³ peut servir de source d'eau dans Énergie.

Pour plus de détails : [Continuité des statistiques](docs/statistics-continuity.md).

### Diagnostic et mises à jour

```bash
ha core logs | grep -iE 'SUEZ historical continuity|SUEZ statistics continuity'
```

Les **données de consommation** sont actualisées toutes les six heures. Les **mises à jour du code** sont proposées par HACS selon sa configuration ; redémarrez Home Assistant Core après une mise à jour du code Python.

### Limitations et confidentialité

- API SUEZ non officielle et susceptible d'évoluer.
- Un seul compteur détecté automatiquement par configuration.
- La continuité historique nécessite une série SUEZ préexistante compatible.
- Les relevés SUEZ peuvent être retardés ou corrigés.
- Les identifiants sont stockés dans l'entrée de configuration Home Assistant ; ne les publiez pas dans les logs, tickets ou captures d'écran.

---

## English

### Features (v0.4.0)

- **Automatic readings** from the **SUEZ Tout sur mon Eau** portal, refreshed **every 6 hours**.
- **Automatic water meter discovery** during setup.
- **Cumulative meter index in m³** and **yesterday's water usage in liters**.
- **Last 7 days consumption**, **month-to-date consumption**, and **7-day daily average**.
- **Estimated monthly water cost** with a configurable **€/m³ water tariff**.
- **Energy dashboard history continuity** for Home Assistant installations with existing legacy SUEZ statistics.
- **Five optional diagnostic sensors**, disabled by default.
- **French and English** interface and documentation.

### Install with HACS

1. Open **HACS → Custom repositories**.
2. Add `https://github.com/papou-github/suez-enhanced` as an **Integration** repository.
3. Install **SUEZ Enhanced** and **restart Home Assistant Core**.
4. Go to **Settings → Devices & services → Add integration → SUEZ Enhanced**.
5. Enter your **SUEZ Tout sur mon Eau** portal credentials. The water meter is detected automatically.

**Requirements:** Home Assistant **2025.1.0 or later**, HACS for custom-repository installation, and a compatible SUEZ portal account.

### Available sensors

| Sensor | Description |
| --- | --- |
| **Meter index** | Cumulative meter reading in m³ (`total_increasing`) |
| **Water usage yesterday** | Previous day's consumption in liters, when available |
| **Consumption last 7 days** | Consolidated consumption over the last seven days, in liters |
| **Consumption this month** | Month-to-date consumption in liters |
| **Daily average (7 days)** | Seven-day average daily consumption, in liters |
| **Estimated month cost** | Estimated monthly cost in euros, using the configured tariff |

Five optional diagnostic sensors report the last sync, last reading day, last historical day, pending historical days and history sync status.

### Home Assistant Energy dashboard history continuity

If your Home Assistant installation already contains a compatible legacy SUEZ statistics series, SUEZ Enhanced can **extend that series under its original statistics ID**, for example `suez_water:<meter_number>_water_consumption_statistics`.

History synchronization is **enabled by default** and can be disabled in the **integration options**.

Safeguards:
- No new legacy statistics series is created if none already exists.
- Existing historical days are never overwritten.
- Only consecutive missing days are appended.
- A **two-day safety delay** applies before import.
- Historical statistics remain in **liters**.

> **Avoid double counting:** if your legacy SUEZ statistics series is already configured as a water source in the Energy dashboard, **do not add Meter index as a second mains-water source**.

For a new installation **without an existing legacy SUEZ series**, the meter-index sensor in m³ can be used as the Energy dashboard water source.

Read more: [Statistics continuity](docs/statistics-continuity.md).

### Diagnostics and updates

```bash
ha core logs | grep -iE 'SUEZ historical continuity|SUEZ statistics continuity'
```

**Consumption readings** refresh every six hours. **Code updates** are offered by HACS according to its configuration; restart Home Assistant Core after updating the Python integration code.

### Limitations and privacy

- Unofficial SUEZ API; upstream changes may break compatibility.
- One water meter is discovered automatically per configuration.
- Historical continuation requires a compatible existing legacy SUEZ statistics series.
- SUEZ readings may arrive late or be corrected.
- Credentials are stored in the Home Assistant config entry; do not share them in logs, issues or screenshots.

---

## Contributing / Contribuer

Bug reports, reproducible issues and improvements are welcome via [GitHub Issues](https://github.com/papou-github/suez-enhanced/issues). **Remove personal data, credentials and meter identifiers** before posting.

Automated checks include HACS validation, Home Assistant hassfest, Python checks and unit tests. See [GitHub Actions](https://github.com/papou-github/suez-enhanced/actions).

**License / Licence :** [MIT](LICENSE) · © 2026 papou-github
