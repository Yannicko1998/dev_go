# Le Foot au Rapport — Scène 8 — Pedri vs Bellingham

**Montage Python 3 + Pillow + OpenCV + FFmpeg**, source Full HD, textes et statistiques animées, 19 séquences, voix originale conservée et ambiance football originale mixée à bas volume.

## Vidéo de référence

Source `Scene_08_Pedri_Bellingham_Premium_1080p(1).mp4` (72,68 s, H.264, 1920×1080, 25 fps, audio AAC). Fichier de la production utilisateur, **non redistribué dans le dépôt GitHub**. Les images utilisées dans le montage proviennent du MP4 et sont celles que l'auteur a fournies.

## Exécution locale

Python 3.11+ et FFmpeg dans `PATH`.

```bash
python -m pip install -r requirements.txt
python montage_scene8.py --input "Scene_08_Pedri_Bellingham_Premium_1080p(1).mp4" --output "Scene_08_Pedri_Bellingham_V4_Premium_Github_1080p25.mp4"
```

Pour 5 secondes de test :

```bash
python montage_scene8.py --input "Scene_08_Pedri_Bellingham_Premium_1080p(1).mp4" --limit 5 --output test.mp4
```

## Structure

- `montage_scene8.py` : moteur complet de rendu image par image et mixage original.
- `scene8_timeline.json` : scènes, statistiques et passages synchronisés d'après une retranscription de la voix (incluse dans le dossier local).
- `sources_verifiees.json` : URLs UEFA/FIFA/RFEF/England Football/L'Équipe.
- `.github/workflows/build-scene8.yml` : workflow de rendu lancé manuellement avec une URL directe d'accès au MP4 source.

## Informations importantes

Les titres de L'Équipe et de la FIFA sont des **références à des articles web**, présentés dans une maquette graphique originale : **ce ne sont pas de véritables couvertures de journaux**. Les posts officiels d'@England et @SEFutbol sont des extraits visuels de publications vérifiées et non des captures d'écran du réseau X. Les interventions d'interviews sont des citations textuelles attribuées, sans montage de vidéos d'interviews téléchargées. Aucune interaction (like/retweet) n'a été inventée.

L'utilisateur peut ajouter les visuels officiels sous licence (trophées, logos, couvertures de journaux, extraits d'interviews) via une déclinaison ultérieure ; à ce stade les pictogrammes de coupes sont créés graphiquement et affichés à côté du nom du tournoi.

## Sources et qualité

Vérifier les droits des photos réutilisées issues du montage source avant toute publication YouTube. Les statistiques apparaissent aux moments de la narration. Aucune statistique n'a été créée sans source officielle. Les trois sorties visées sont le MP4 final, le rapport JSON d'export et le projet Python modifiable.