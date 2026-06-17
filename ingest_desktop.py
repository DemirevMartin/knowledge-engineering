""" Execute directly to ingest the local Neo4j Desktop database. """

import os
import pandas as pd
from neo4j import GraphDatabase

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "nutrismart12311")
BATCH_SIZE = 500

PROJECT_DIR = r"C:\Users\Martin\Desktop\Quarter4\Knowledge Engineering\Project\knowledge-engineering"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val):
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _batches(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def _run_batched(driver, load_fn, rows):
    total = len(rows)
    for batch in _batches(rows, BATCH_SIZE):
        with driver.session() as s:
            s.execute_write(load_fn, batch)
    print(f"  Loaded {total:,} rows via {load_fn.__name__}")


# ---------------------------------------------------------------------------
# Constraints and indexes
# ---------------------------------------------------------------------------

def create_constraints(driver):
    statements = [
        # Uniqueness constraints (automatically create a backing index)
        "CREATE CONSTRAINT recipe_id IF NOT EXISTS FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE",
        "CREATE CONSTRAINT ingredient_name IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.ingredient_name IS UNIQUE",
        "CREATE CONSTRAINT np_id IF NOT EXISTS FOR (np:NutritionalProfile) REQUIRE np.recipe_id IS UNIQUE",
        # Lookup indexes
        "CREATE INDEX recipe_rating IF NOT EXISTS FOR (r:Recipe) ON (r.avg_rating)",
        "CREATE INDEX recipe_carbon_tier IF NOT EXISTS FOR (r:Recipe) ON (r.carbon_tier)",
    ]
    with driver.session() as s:
        for stmt in statements:
            s.run(stmt)
    print("Constraints and indexes created.")


# ---------------------------------------------------------------------------
# Clear database
# ---------------------------------------------------------------------------

def clear_db(driver):
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
    print("Database cleared.")


# ---------------------------------------------------------------------------
# Recipe nodes
# ---------------------------------------------------------------------------

def _load_recipe_batch(tx, batch):
    tx.run(
        """
        UNWIND $rows AS row
        MERGE (r:Recipe {recipe_id: row.recipe_id})
        SET r.name               = row.name,
            r.category           = row.category,
            r.cooking_method     = row.cooking_method,
            r.difficulty         = row.difficulty,
            r.spice_level        = row.spice_level,
            r.meal_type          = row.meal_type,
            r.is_vegetarian      = row.is_vegetarian,
            r.is_vegan           = row.is_vegan,
            r.is_gluten_free     = row.is_gluten_free,
            r.is_halal           = row.is_halal,
            r.is_traditional     = row.is_traditional,
            r.is_festival_special = row.is_festival_special,
            r.prep_time_min      = row.prep_time_min,
            r.cook_time_min      = row.cook_time_min,
            r.total_time_min     = row.total_time_min,
            r.servings           = row.servings,
            r.avg_rating         = row.avg_rating,
            r.total_reviews      = row.total_reviews,
            r.estimated_cost_usd = row.estimated_cost_usd,
            r.date_added         = row.date_added
        """,
        rows=batch,
    )


def load_recipes(driver):
    recipes_df = pd.read_csv(os.path.join(PROJECT_DIR, "preprocessing", "recipes_master.csv"))
    nutrition_df = pd.read_csv(os.path.join(PROJECT_DIR, "preprocessing", "recipe_nutrition.csv"))
    df = recipes_df.merge(nutrition_df, on="recipe_id", how="left")

    rows = []
    for _, r in df.iterrows():
        rows.append({
            "recipe_id":           str(r["recipe_id"]),
            "name":                str(r["recipe_name"]),
            "category":            str(r.get("category", "")),
            "cooking_method":      str(r.get("cooking_method", "")),
            "difficulty":          str(r.get("difficulty", "")),
            "spice_level":         str(r.get("spice_level", "")),
            "meal_type":           str(r.get("meal_type", "")),
            "is_vegetarian":       bool(r.get("is_vegetarian", False)),
            "is_vegan":            bool(r.get("is_vegan", False)),
            "is_gluten_free":      bool(r.get("is_gluten_free", False)),
            "is_halal":            bool(r.get("is_halal", False)),
            "is_traditional":      bool(r.get("is_traditional", False)),
            "is_festival_special": bool(r.get("is_festival_special", False)),
            "prep_time_min":       _safe_float(r.get("prep_time_minutes")),
            "cook_time_min":       _safe_float(r.get("cook_time_minutes")),
            "total_time_min":      _safe_float(r.get("total_time_minutes")),
            "servings":            _safe_float(r.get("servings")),
            "avg_rating":          _safe_float(r.get("rating")),
            "total_reviews":       _safe_float(r.get("review_count")),
            "estimated_cost_usd":  _safe_float(r.get("estimated_cost_usd")),
            "date_added":          str(r.get("date_added", "")),
        })

    _run_batched(driver, _load_recipe_batch, rows)


# ---------------------------------------------------------------------------
# Ingredient nodes
# ---------------------------------------------------------------------------

def _load_ingredient_batch(tx, batch):
    tx.run(
        """
        UNWIND $rows AS row
        MERGE (i:Ingredient {ingredient_name: row.ingredient_name})
        SET i.co2_kg_per_kg = row.co2_kg_per_kg,
            i.usda_tier     = row.usda_tier,
            i.category      = row.category
        """,
        rows=batch,
    )


def load_ingredients(driver):
    co2_df = pd.read_csv(os.path.join(PROJECT_DIR, "preprocessing", "ingredient_co2.csv"))
    grounded = pd.read_csv(
        os.path.join(PROJECT_DIR, "preprocessing", "recipe_ingredients_grounded.csv"),
    )

    # Build lookups from co2 file (column is 'ingredient', not 'ingredient_name')
    co2_lu = dict(zip(
        co2_df["ingredient"].str.strip().str.lower(),
        co2_df["co2_kg_per_kg"],
    ))

    # One row per unique ingredient; carry usda_tier from grounded file
    tier_lu = (
        grounded
        .dropna(subset=["ingredient_name"])
        .drop_duplicates("ingredient_name")
        .set_index("ingredient_name")["usda_tier"]
        .to_dict()
    )

    category_lu = (
        grounded
        .dropna(subset=["ingredient_name"])
        .drop_duplicates("ingredient_name")
        .assign(ingredient_name=lambda x: x["ingredient_name"].str.strip().str.lower())
        .set_index("ingredient_name")["category"]
        .to_dict()
    ) if "category" in grounded.columns else {}

    all_names = grounded["ingredient_name"].str.strip().str.lower().dropna().unique()

    rows = [
        {
            "ingredient_name": name,
            "co2_kg_per_kg":   _safe_float(co2_lu.get(name)),
            "usda_tier":       str(tier_lu.get(name, "generic")),
            "category":        str(category_lu.get(name, "Others")),
        }
        for name in all_names
    ]

    _run_batched(driver, _load_ingredient_batch, rows)


# ---------------------------------------------------------------------------
# HAS_INGREDIENT edges
# ---------------------------------------------------------------------------

def _load_has_ingredient_batch(tx, batch):
    tx.run(
        """
        UNWIND $rows AS row
        MATCH (r:Recipe     {recipe_id:       row.recipe_id})
        MATCH (i:Ingredient {ingredient_name: row.ingredient_name})
        MERGE (r)-[h:HAS_INGREDIENT]->(i)
        SET h.grams     = row.grams,
            h.co2e_kg   = row.co2e_kg,
            h.usda_tier = row.usda_tier,
            h.qty_amount = row.qty_amount,
            h.qty_unit   = row.qty_unit
        """,
        rows=batch,
    )


def load_has_ingredient(driver):
    df = pd.read_csv(os.path.join(PROJECT_DIR, "preprocessing", "recipe_ingredients_grounded.csv"))
    df["ingredient_name"] = df["ingredient_name"].str.strip().str.lower()

    rows = []
    for _, r in df.iterrows():
        grams = _safe_float(r.get("grams"))
        # Use pre-computed co2e_kg column from grounded file if present
        co2e = _safe_float(r.get("co2e_kg"))
        if co2e is None:
            co2_per_kg = _safe_float(r.get("co2_kg_per_kg"))
            if grams is not None and co2_per_kg is not None:
                co2e = round(grams / 1000.0 * co2_per_kg, 6)

        rows.append({
            "recipe_id":       str(r["recipe_id"]),
            "ingredient_name": str(r["ingredient_name"]),
            "grams":           grams,
            "co2e_kg":         co2e,
            "usda_tier":       str(r.get("usda_tier", "generic")),
            "qty_amount":      _safe_float(r.get("qty_amount")),
            "qty_unit":        str(r.get("qty_unit", "")),
        })

    _run_batched(driver, _load_has_ingredient_batch, rows)


# ---------------------------------------------------------------------------
# Inference rules (post-load derived properties)
# ---------------------------------------------------------------------------

def apply_inference_rules(driver):
    """R1 — total_co2e = SUM(HAS_INGREDIENT.co2e_kg), carbon_tier classification."""
    with driver.session() as s:
        result = s.run(
            """
            MATCH (r:Recipe)-[h:HAS_INGREDIENT]->(:Ingredient)
            WHERE h.co2e_kg IS NOT NULL
            WITH r, sum(h.co2e_kg) AS total
            SET r.total_co2e  = round(total, 4),
                r.carbon_tier = CASE
                    WHEN total < 2 THEN 'low'
                    WHEN total <= 8 THEN 'medium'
                    ELSE 'high'
                END
            RETURN count(r) AS updated
            """
        )
        updated = result.single()["updated"]
    print(f"  Inference R1 applied: {updated:,} recipes updated with total_co2e and carbon_tier")


# ---------------------------------------------------------------------------
# NutritionalProfile nodes (1-to-1 with Recipe, mandatory per ontology)
# ---------------------------------------------------------------------------

def create_nutritional_profiles(driver):
    with driver.session() as s:
        s.run(
            """
            MATCH (r:Recipe)
            MERGE (np:NutritionalProfile {recipe_id: r.recipe_id})
            SET np.calories_per_serving = r.calories,
                np.protein_g            = r.protein_g,
                np.fat_g                = r.fat_g,
                np.sugar_g              = r.sugar_g,
                np.fiber_g              = r.fiber_g,
                np.carbohydrates_g      = r.carbohydrates_g
            MERGE (r)-[:HAS_NUTRITION]->(np)
            """
        )
        count = s.run("MATCH (np:NutritionalProfile) RETURN count(np) AS n").single()["n"]
    print(f"  NutritionalProfile nodes created: {count:,}")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(driver):
    checks = {
        "Recipe nodes":             "MATCH (r:Recipe)               RETURN count(r) AS n",
        "Ingredient nodes":         "MATCH (i:Ingredient)           RETURN count(i) AS n",
        "NutritionalProfile nodes": "MATCH (np:NutritionalProfile)  RETURN count(np) AS n",
        "HAS_INGREDIENT edges":     "MATCH ()-[h:HAS_INGREDIENT]->()     RETURN count(h) AS n",
        "HAS_NUTRITION edges":      "MATCH ()-[n:HAS_NUTRITION]->()      RETURN count(n) AS n",
        "Recipes w/ carbon_tier":   "MATCH (r:Recipe) WHERE r.carbon_tier IS NOT NULL RETURN count(r) AS n",
        "Recipes w/ total_co2e":    "MATCH (r:Recipe) WHERE r.total_co2e  IS NOT NULL RETURN count(r) AS n",
        "HAS_INGREDIENT w/ co2e":   "MATCH ()-[h:HAS_INGREDIENT]->() WHERE h.co2e_kg IS NOT NULL RETURN count(h) AS n",
    }

    print("\n=== Graph verification ===")
    with driver.session() as s:
        for label, q in checks.items():
            n = s.run(q).single()["n"]
            print(f"  {label:<30} {n:>10,}")

    with driver.session() as s:
        labels = [r["label"] for r in s.run("CALL db.labels() YIELD label RETURN label ORDER BY label").data()]
        rels = [r["relationshipType"] for r in s.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType").data()]

    print(f"\n  Node labels:         {labels}")
    print(f"  Relationship types:  {rels}")

    expected_labels = {"Ingredient", "NutritionalProfile", "Recipe"}
    expected_rels = {"HAS_INGREDIENT", "HAS_NUTRITION"}
    missing_l = expected_labels - set(labels)
    missing_r = expected_rels - set(rels)

    if missing_l or missing_r:
        print(f"\n  WARNING — missing labels: {missing_l}, missing rels: {missing_r}")
    else:
        print("\n  Graph matches ontology schema. ✓")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Connecting to Neo4j Desktop at {URI} ...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        driver.verify_connectivity()
        print("Connected to Neo4j Desktop.\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        raise

    clear_db(driver)
    create_constraints(driver)

    print("\nIngesting data...")
    load_recipes(driver)
    load_ingredients(driver)
    load_has_ingredient(driver)

    print("\nApplying inference rules...")
    apply_inference_rules(driver)

    print("\nCreating NutritionalProfile nodes...")
    create_nutritional_profiles(driver)

    verify(driver)

    driver.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
