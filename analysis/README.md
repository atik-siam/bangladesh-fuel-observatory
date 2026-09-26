# Reproducible research layer

`01_research_pipeline.ipynb` is the human-readable analysis companion to the production scripts.

It follows the same sequence as the website:

1. load the version-controlled data;
2. inspect coverage and benchmark mapping;
3. construct Tk/L market-equivalent series;
4. audit official-event eligibility;
5. build the expanding-calibration estimator;
6. compare with the naive previous-price baseline;
7. inspect exploratory pass-through regression;
8. inspect walk-forward predictions;
9. evaluate window sensitivity;
10. export the same model JSON used by the website.

The notebook does not use random train/test shuffling. The main evaluation remains time ordered.
