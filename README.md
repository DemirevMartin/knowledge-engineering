# NutriSmart Knowledge Graph for Culinary Sustainability

A knowledge graph that links South Asian recipes to ingredient-level carbon emission factors and nutritional data, built to generate recipe-level "eco-scores" (kg CO₂eq per recipe).

## Research questions

- **RQ1**: Which ingredients contribute most to recipe-level carbon footprint, and how often do they appear in the top-*k* highly rated recipes?
- **RQ2**: Which top-*N* co-occurring ingredient pairs (and their average CO₂e) emerge among the top-*k* high-carbon recipes?
- **RQ3**: Do higher-carbon recipes differ nutritionally from low-carbon ones, and does user engagement reflect that trade-off?

## Source datasets

| Name | Source | Role |
|------|--------|------|
| Dataset Foods | Kaggle "10K South Asian Recipes" | Recipes, ingredients, nutrition, ratings |
| Dataset Wolfram | Wolfram Food Carbon Footprint | Primary CO₂e emission factors (538 foods) |
| OWID GHG | Our World in Data | Fallback CO₂e for 4 foods absent from Wolfram |
| Dataset Quantities | USDA FoodData Central SR Legacy (2018) | Gram-weight conversion (culinary unit → grams) |


## Pipeline overview

The three sources are mutually incompatible as delivered (free-text culinary quantities vs. per-kg emission factors vs. no shared ingredient vocabulary). A three-stage pipeline reconciles them:

1. **Ingredient canonicalisation + CO₂e assignment** — collapse 103,908 raw ingredient line items to 58 canonical ingredients; assign a CO₂e factor to each (Wolfram primary, OWID fallback → 100% coverage).
2. **Gram-weight grounding** — convert each ingredient quantity to grams via a three-tier procedure (USDA SR Legacy lookup → exact-mass passthrough → fixed/density fallback), recorded per row in `usda_tier`.
3. **Recipe-level CO₂e** — sum `qty × g_per_unit × co2_kg_per_kg / 1000` over a recipe's ingredients → one score per recipe (9,997 recipes).

## Repository structure

```
.
├── main.tex                          # Datasheet / report (LaTeX source)
├── ingest_desktop.py                 # Loads CSVs into Neo4j; applies inference rule R1
├── gdb.ipynb                         # Graph DB queries — RQ1/RQ2/RQ3 against Neo4j
├── recipe_co2.csv                    # Final per-recipe CO₂e scores (pipeline output)
├── recipe_ingredients_grounded.csv   # Per-row grounded quantities (grams, co2e_kg, usda_tier)
│
├── preprocessing/                    # Stage 1–3 inputs, notebooks, and outputs
│   ├── main.ipynb                    #   Ingredient canonicalisation + CO₂e assignment (Stage 1)
│   ├── quantities.ipynb              #   Gram-weight grounding via USDA SR Legacy (Stage 2)
│   ├── wolfram_json_to_excel.py      #   Wolfram JSON → Excel converter (data exchange)
│   ├── recipes_master.csv            #   Raw: recipe master metadata
│   ├── recipe_ingredients.csv        #   Raw: recipe ↔ ingredient line items
│   ├── recipe_nutrition.csv          #   Raw: per-recipe nutrition
│   ├── recipes_ingredients_master.csv
│   ├── Wolfram_Food_Carbon_Footprint.xlsx
│   ├── ingredient_co2.csv            #   Output: canonical ingredient → CO₂e + source
│   ├── recipe_co2.csv                #   Output: per-recipe CO₂e (copy of root)
│   ├── recipe_ingredients_grounded.csv
│   └── FoodData_Central_sr_legacy_food_csv_2018-04/
│       ├── food.csv
│       ├── food_portion.csv          #   The portion table used for gram-weight lookup
│       └── measure_unit.csv
│
├── visualization_preprocessing/      # Figures used in the report
│   ├── data_sources.py               #   Generates the pipeline diagram
│   ├── data_sources_exchange.png     #   Pipeline diagram (Fig. 1 in report)
│   ├── visualization_ingredients.ipynb
│   ├── visualization_quantities.ipynb
│   └── figures/                      #   04_/05_ coverage & CO₂e charts, q01–q09 tier charts
│
└── RQ2 results/                      # RQ2 query, findings, and visualization
    ├── RQ2 Neo4j query
    ├── RQ2 Findings.csv / .json
    └── RQ2 Visualisation.png
```

## Running the pipeline

1. **Preprocess** — run `preprocessing/main.ipynb` then
   `preprocessing/quantities.ipynb` to regenerate `ingredient_co2.csv`,
   `recipe_ingredients_grounded.csv`, and `recipe_co2.csv`.
2. **Ingest** — start a local Neo4j instance, then `python ingest_desktop.py`.
   - Connection settings (`URI`, `AUTH`) and an absolute `PROJECT_DIR` are
     **hardcoded** near the top of `ingest_desktop.py` — update these for your
     machine before running.
3. **Figures** — `visualization_preprocessing/` notebooks and `data_sources.py`
   regenerate the preprocessing visualizations.