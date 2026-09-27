# POC marimo dans Astro

Page : `/lab/marimo/`. Le notebook simule des comptages de photons, avec deux
curseurs qui relancent réellement Python dans le navigateur. Un lien ouvre le
même notebook dans un éditeur de cellules.

## Démarrer localement

Depuis la racine du dépôt, avec Node installé :

```bash
# Installation initiale, dans un environnement distinct des notebooks MyST
python3.12 -m venv interactive/.venv
interactive/.venv/bin/python -m pip install -r interactive/requirements.txt
npm ci

# Exporter les deux versions, puis démarrer Astro
npm run marimo:export
npm run dev
```

Ouvrir <http://localhost:4321/lab/marimo/> (ou le port indiqué par Astro).
Si le venv est créé avec `uv`, installer avec
`uv pip install --python interactive/.venv/bin/python -r interactive/requirements.txt`.

## Éditer

```bash
# Éditeur marimo local : les sauvegardes modifient le fichier source
npm run marimo:edit

# Après sauvegarde, republier localement les versions navigateur
npm run marimo:export
```

La source est `interactive/photon_counts.py`. La présentation utilise
`interactive/theme.css`. Recharger la page Astro après l’export.

Le lien **Edit the code** dans la page ouvre une copie qui s’exécute en
WebAssembly. Cliquer sur ▶ en bas à droite pour exécuter les cellules, puis
relancer après modification du code. Les modifications ne changent ni le dépôt
ni le fichier source local : télécharger le notebook depuis cet éditeur pour les conserver.

Pour réexporter automatiquement la version intégrée pendant l’édition du Python,
laisser cette commande tourner dans un autre terminal :

```bash
interactive/.venv/bin/python -m marimo export html-wasm \
  interactive/photon_counts.py \
  -o public/notebooks/marimo/index.html --mode run --no-sandbox --force --watch
```

Ce watcher concerne le Python et la version `run` uniquement. Après une
modification du CSS ou pour actualiser aussi l’éditeur exporté, relancer
`npm run marimo:export`, puis recharger le navigateur.

## Build et GitHub Pages

```bash
# Export marimo + build Astro, à partir des autres articles déjà générés
npm run marimo:build
npm run preview

# Vérifications
npm run check
interactive/.venv/bin/python -m marimo check --strict interactive/photon_counts.py
```

`scripts/build_marimo.py` écrit `index.html`, `edit.html` et leurs assets partagés
dans `public/notebooks/marimo/`. Astro les copie dans `dist/` avec le site.
Les exports et le venv sont ignorés par Git ; seules les sources sont versionnées.
Le workflow GitHub Pages installe marimo dans un venv séparé et exporte les deux
versions avant le build Astro. `npm run build:all` inclut aussi cette étape et
nécessite, comme avant, l’environnement des notebooks MyST pour leur exécution.

**GitHub Pages suffit : aucun serveur Python n’est nécessaire en production.**
Le navigateur télécharge Pyodide et les dépendances Python au premier lancement.
Les assets de l’interface marimo sont servis avec le site. L’export n’est donc
pas une garantie de fonctionnement hors ligne ; le premier chargement peut
prendre plusieurs dizaines de secondes selon la connexion.

La démo ne dépend que de marimo et de la bibliothèque standard de Python.
Un notebook utilisant JAX ou une autre bibliothèque native devra être adapté
avant d’être exécutable en WebAssembly. Le rendu Astro autour du notebook reste
statique ; le contenu de l’iframe nécessite JavaScript.

La POC a une route dédiée et n’ajoute pas d’article au blog. Aucun push ni
déploiement n’est nécessaire pour la tester localement.

## Retrouver l’état précédent

- Sauvegarde avant la POC : commit `3a3347a7`.
- Tag : `before-marimo-poc-2026-09-27`.
- Branche de travail : `codex/marimo-poc`.

Pour inspecter la sauvegarde dans un autre dossier, sans changer la branche courante :

```bash
git worktree add --detach ../site-before-marimo before-marimo-poc-2026-09-27
```

Documentation : [exports WebAssembly](https://docs.marimo.io/guides/exporting/webassembly_html/)
et [GitHub Pages](https://docs.marimo.io/guides/publishing/github/#publish-to-github-pages).
