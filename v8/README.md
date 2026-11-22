# LE FOOT AU RAPPORT — SCÈNE 8 V8 PREMIUM

Vidéo **Pedri vs Jude Bellingham — Le poids des grands tournois**, 72,68 secondes, Full HD 1920×1080, 25 i/s.

## Ce qui change en V8

- Véritable logo fourni par l'auteur : bleu nuit, vert et blanc ; pas de minuterie.
- Coupe Henri-Delaunay / Coupe du Monde avec découpes alpha sur les plans correspondants. **Ces deux images sont des rendus illustratifs et non des photos officielles**.
- Texte intégré aux photographies plein écran, sans empilement de rectangles type PowerPoint.
- Statistiques animées à la seconde où elles sont prononcées : précision de passes 65/66 (98,5%), finales Euro, résultats 2026, 7 buts et 1 passe décisive, rang et graphique des buteurs.
- Extraits de presse attribués en légende originale, sans fausses unes ni fausses captures de réseaux sociaux.
- Ambiance de stade synthétique en fond, mixée sous la voix off.
- Un récapitulatif final illustratif avec logo officiel incrusté.

## Reproduire

Vous devez posséder **le MP4 source fourni dans le chat** (non publié sur GitHub). Les autres éléments nécessaires, code, timeline et images, se trouvent dans le dossier `v8` du dépôt, notamment les médias `.b64` directement décodés par le script.

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
python -m pip install -r v8/requirements.txt
python v8/montage_scene8_v8.py --input "/chemin/Scene_08_Pedri_Bellingham_Premium_1080p(1).mp4" --output "scene8_v8_finale.mp4"
```

Les fichiers déjà présents dans `v8/assets` au format `.b64` sont les illustrations optimisées du projet. Le ZIP téléchargeable dans le chat contient les images haute résolution originales.

## Vérifications

- Durée et piste voix off synchronisées avec `scene8_timeline.json` et la transcription `Scene_08_Voix_Off_Transcription.srt`.
- Euro 2020 (joué en 2021) distinct de l'Euro 2024.
- Images contextuelles : les photos de joueurs ou de stade servant d'illustration ne sont **pas** présentées comme des captures des rencontres concernées quand ce n'est pas démontré.
- Les images de trophées et le collage de fin ont été **créés à titre illustratif** pour l'auteur. Toute publication avec des images réelles supplémentaires suppose de vérifier leur licence.