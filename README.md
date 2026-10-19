# SUEZ Enhanced

[🇫🇷 Français](#français) · [🇬🇧 English](#english)

---

## Français

**SUEZ Enhanced** est une intégration personnalisée pour Home Assistant qui récupère les relevés du portail **Tout sur mon Eau (SUEZ)** et peut prolonger les statistiques historiques de consommation d'eau utilisées par le tableau de bord Énergie.

> **Avertissement :** projet communautaire non officiel, non affilié à SUEZ. L'API utilisée peut changer. Effectuez une sauvegarde Home Assistant avant toute première synchronisation de statistiques historiques.

### Installation avec HACS

1. Dans **HACS → Dépôts personnalisés**, ajoutez `https://github.com/papou-github/suez-enhanced` comme dépôt de type **Integration**.
2. Installez **SUEZ Enhanced**, puis **redémarrez Home Assistant Core**.
3. Ouvrez **Paramètres → Appareils et services → Ajouter une intégration → SUEZ Enhanced**.
4. Saisissez les identifiants du portail SUEZ. Le compteur est détecté automatiquement.

### Capteurs

| Capteur | Description |
| --- | --- |
| **Meter index** | Index du compteur en m³ (`total_increasing`). |
| **Water usage yesterday** | Consommation de la veille en litres, lorsqu'elle est disponible. |

Les données SUEZ sont récupérées **toutes les 6 heures**.

### Continuité de l'historique Énergie

Lorsque l'ancienne série de statistiques SUEZ existe, l'intégration peut la prolonger sous son **identifiant d'origine**, par exemple `suez_water:<numéro_de_compteur>_water_consumption_statistics`. Cette synchronisation est **activée par défaut** et peut être désactivée dans les **options de l'intégration**.

Protections : aucune création d'une nouvelle série historique en l'absence de l'ancienne, aucune réécriture des journées existantes, ajout des seules journées consécutives et **délai de sécurité de deux jours** avant import. Les statistiques historiques restent en **litres**.

**Attention au double comptage :** si la série historique SUEZ est déjà sélectionnée dans Énergie, n'ajoutez pas aussi le capteur **Meter index** comme deuxième source d'eau du réseau.

Pour les nouvelles installations sans historique SUEZ préexistant, le capteur d'index en m³ peut être utilisé comme source dans Énergie.

### Diagnostic

```bash
ha core logs | grep -iE 'SUEZ historical continuity|SUEZ statistics continuity'
```

### Mises à jour

Les **relevés** sont actualisés automatiquement toutes les 6 heures. Les **mises à jour du code** sont proposées par HACS selon sa configuration. Après une mise à jour du code Python, redémarrez **Home Assistant Core**. L'intégration ne force ni installation ni redémarrage.

### Limitations et confidentialité

- API SUEZ non officielle, susceptible d'évoluer.
- Découverte automatique d'un seul compteur par configuration.
- La reprise historique nécessite une série SUEZ compatible déjà présente dans Home Assistant.
- Les données publiées par SUEZ peuvent être retardées ou corrigées.
- Les identifiants sont conservés dans l'entrée de configuration Home Assistant ; ne les publiez pas dans les journaux ou les captures.

### Développement

Les workflows GitHub Actions vérifient **HACS**, **hassfest**, la syntaxe Python et les fichiers JSON. Consultez les résultats dans [GitHub Actions](https://github.com/papou-github/suez-enhanced/actions).

---

## English

**SUEZ Enhanced** is a custom Home Assistant integration that retrieves readings from the **Tout sur mon Eau (SUEZ)** portal and can continue existing water-consumption statistics used by the Energy dashboard.

> **Disclaimer:** This is an unofficial community project and is not affiliated with SUEZ. The underlying API may change. Create a full Home Assistant backup before the first historical-statistics synchronization.

### Installation with HACS

1. In **HACS → Custom repositories**, add `https://github.com/papou-github/suez-enhanced` as an **Integration** repository.
2. Install **SUEZ Enhanced**, then **restart Home Assistant Core**.
3. Open **Settings → Devices & services → Add integration → SUEZ Enhanced**.
4. Enter your SUEZ portal credentials. The water meter is discovered automatically.

### Sensors

| Sensor | Description |
| --- | --- |
| **Meter index** | Meter reading in m³ (`total_increasing`). |
| **Water usage yesterday** | Previous day's consumption in liters, when available. |

SUEZ data is fetched **every 6 hours**.

### Energy dashboard history continuity

When a legacy SUEZ statistics series already exists, the integration can extend it using its **original statistics ID**, such as `suez_water:<meter_number>_water_consumption_statistics`. Synchronization is **enabled by default** and can be disabled in the **integration options**.

Safeguards: no new legacy series is created if none exists, existing days are not overwritten, only consecutive missing days are appended, and readings are imported after a **two-day safety delay**. Historical statistics remain in **liters**.

**Avoid double counting:** if your legacy SUEZ statistics series is already selected in the Energy dashboard, do not add **Meter index** as another mains-water source.

For new installations without existing SUEZ statistics, the meter-index sensor in m³ can be used as an Energy dashboard source.

### Diagnostics

```bash
ha core logs | grep -iE 'SUEZ historical continuity|SUEZ statistics continuity'
```

### Updates

**Water readings** refresh automatically every 6 hours. **Integration code updates** are offered through HACS according to its settings. Restart **Home Assistant Core** after updating Python integration code. The integration does not force updates or restarts.

### Limitations and privacy

- Unofficial SUEZ API, subject to change.
- Automatic discovery of one meter per configuration.
- History continuation requires an existing compatible SUEZ statistics series.
- SUEZ readings may be delayed or revised.
- Credentials are stored in the Home Assistant config entry; never share them in logs or screenshots.

### Development

GitHub Actions workflows run **HACS**, **hassfest**, Python syntax, and JSON checks. See [GitHub Actions](https://github.com/papou-github/suez-enhanced/actions) for the current results.

---

MIT License · © 2026 papou-github
