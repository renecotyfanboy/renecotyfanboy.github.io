# Aide-mémoire local — notebooks et site

Toutes les commandes partent de la racine du projet. Ce fichier reste hors du contenu du site.

## Démarrer une session

**Terminal 1 — générer les articles et servir le site :**

```bash
cd /Users/sdupourque/VSCodeProjects/renecotyfanboy.github.io
source notebooks/.venv/bin/activate
npm run notebooks
npm run dev
```

Ouvrir <http://localhost:4321/blog/> ou, pour le brouillon JAX,
<http://localhost:4321/blog/jax-tutorial/>. Si le port est occupé, utiliser l’adresse affichée par Astro.

**Terminal 2 — après avoir enregistré des modifications :**

```bash
cd /Users/sdupourque/VSCodeProjects/renecotyfanboy.github.io
source notebooks/.venv/bin/activate

# Texte ou métadonnées uniquement : réutiliser les résultats en cache
npm run notebooks:fast

# Code Python, paramètres ou graphiques modifiés : recalculer
npm run notebooks
```

Choisir l’une des deux dernières commandes selon la modification. Astro recharge
la page lorsque l’article généré change. Il ne surveille pas les sources dans
`notebooks/` pour relancer Python : cette régénération reste à déclencher.
L’édition se fait dans ton éditeur ; le navigateur affiche le rendu et les graphiques interactifs.

Arrêter le serveur avec `Ctrl+C`. Pour quitter l’environnement Python : `deactivate`.

## Commandes à retenir

| Commande | Effet |
| --- | --- |
| `source notebooks/.venv/bin/activate` | Activer Python et les dépendances du projet dans le terminal courant. |
| `npm run notebooks` | Exécuter **tous** les notebooks, générer les articles, les graphiques et le cache. |
| `npm run notebooks:fast` | Régénérer **tous** les articles avec les résultats en cache, sans exécuter Python. |
| `npm run dev` | Servir le site avec rechargement automatique et brouillons visibles. |
| `npm run dev -- --open` | Même chose, en ouvrant le navigateur. |
| `npm run dev -- --port 4322` | Utiliser un autre port. |
| `npm run build:all` | Exécuter les notebooks puis construire le site de production dans `dist/`. |
| `npm run build` | Construire uniquement le site, à partir des articles et graphiques déjà générés. |
| `npm run preview` | Servir le dernier `dist/` construit, sans régénération ni rechargement à l’édition. |
| `npm run check` | Vérifier les types et les diagnostics Astro. |

Les scripts de génération n’ont actuellement ni sélection d’un notebook individuel,
ni option `--watch`. Équivalents Python :

```bash
python3 scripts/build_notebooks.py
python3 scripts/build_notebooks.py --no-execute
```

## Où éditer et où retrouver le résultat

| Fichier / dossier | Rôle |
| --- | --- |
| `notebooks/<slug>.md` | Source MyST à éditer : texte, métadonnées et cellules Python. |
| `src/content/posts/<slug>.md` | Article généré ; toute modification directe sera écrasée. |
| `public/charts/<slug>/` | Graphiques interactifs générés, ignorés par Git. |
| `notebooks/.cache/<slug>.json` | Résultats du dernier calcul pour le mode rapide. |
| `/blog/<slug>/` | Adresse de l’article sur le site. |

Les articles rédigés directement dans `src/content/posts/` et dépourvus de
`generated: true` peuvent être édités directement ; `npm run dev` suffit pour eux.

## Créer un nouveau notebook

Créer `notebooks/mon-article.md` avec cette structure, puis lancer `npm run notebooks` :

````markdown
---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: myst
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
title: Mon article
description: Une courte description.
date: 2026-09-27
tags: [python]
source: notebook
draft: true
---

## Première expérience

Du texte, puis une cellule exécutée pendant la génération :

```{code-cell} python
print(2 + 2)
```
````

Adapter la date et le slug. Un bloc `{code-cell} python` est exécuté ; un bloc
`python` ordinaire est seulement affiché. Ne pas renseigner `generated` ou
`notebook` : le script les ajoute à l’article généré.

`draft: true` rend l’article visible en développement, mais l’exclut de la
production et de `npm run preview`. Pour l’inclure en production, retirer ce
champ ou mettre `draft: false` dans **la source**, puis régénérer.

## Installation initiale, si nécessaire

L’environnement `notebooks/.venv/` et `node_modules/` existent déjà sur cette
machine. Sur une nouvelle installation, utiliser Python 3.12 et Node ≥ 22.12.0
(la CI du projet utilise Node 22) :

```bash
cd /Users/sdupourque/VSCodeProjects/renecotyfanboy.github.io
npm ci
python3.12 -m venv notebooks/.venv
source notebooks/.venv/bin/activate
python3 -m pip install -r notebooks/requirements.txt
python3 -m ipykernel install --sys-prefix --name python3 --display-name "Python 3"
```

`requirements.txt` décrit les dépendances ; `requirements.lock` est la liste
figée utilisée en CI, résolue pour Linux / Python 3.12. Ajouter les bibliothèques
nécessaires à de nouvelles cellules à l’environnement et aux dépendances du projet.

## Vérifier le rendu de production localement

Avec l’environnement Python activé :

```bash
npm run build:all
npm run preview
```

Ouvrir l’adresse indiquée dans le terminal. Ces commandes construisent et servent
le site localement ; elles ne le déploient pas. Relancer le build après une
modification pour actualiser cet aperçu.

## Si le rendu ne suit pas

- **Texte inchangé dans le navigateur :** enregistrer la source puis lancer
  `npm run notebooks:fast` dans le second terminal.
- **`no cached run` :** lancer `npm run notebooks` une première fois. Le mode
  rapide exige un cache pour chaque notebook, y compris les nouveaux brouillons.
- **Résultat absent après modification d’une cellule :** lancer `npm run notebooks`.
  Le mode rapide laisse vides les sorties des cellules dont le code a changé.
  Il ne recalcule pas non plus les cellules qui dépendent de ce code ou de données modifiées.
- **Graphiques absents :** lancer `npm run notebooks` ; le mode rapide et
  `npm run build` ne recréent pas les fichiers HTML de `public/charts/`.
- **Brouillon absent :** utiliser `npm run dev` ; les builds de production l’excluent.
- **`ModuleNotFoundError` :** vérifier l’activation du venv et ses dépendances.
  `python3 -m jupyter kernelspec list` permet de vérifier le kernel `python3`.

La génération traite aussi les brouillons. Renommer ou supprimer une source
entraîne la suppression de son ancien article généré au prochain passage du script.
