# Third-party data in this directory

- `yamnet.tflite` and `yamnet_class_map.csv`: YAMNet, by Google, Apache License 2.0.
  Model from https://tfhub.dev/google/lite-model/yamnet/tflite/1 and class map from
  https://github.com/tensorflow/models/tree/master/research/audioset/yamnet.
  SHA-256 of the model: `141fba1cdaae842c816f28edc4937e8b4f0af4c8df21862ccc6b52dc567993c3`.
- `places.tsv.gz` and `countries.json`: derived from the GeoNames `cities15000` and
  `countryInfo` dumps (https://www.geonames.org), Creative Commons Attribution 4.0.
  Rebuilt with `scripts/build_places.py`.

Fonts in `api/app/fonts`: Bebas Neue (SIL Open Font License 1.1), Yellowtail and
Special Elite (Apache License 2.0), all from https://github.com/google/fonts.
