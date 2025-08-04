#!/usr/bin/env python3
"""
Integrated Preference + Analysis Recommendation Pipeline for SmartBeauty
========================================================================
This utility combines **skin analysis**, **explicit user preferences** and
**allergen safety** to generate personalised product recommendations.

Key Features
------------
1.  Fetches *skin analysis* (utility.get_analysis.get_user_analysis)
2.  Fetches *user preferences* (utility.get_preference.get_preference)
3.  Uses DB-stored user/profile embeddings (assumes `users.embedding` is already populated)
4.  Merges concerns coming from
      • image analysis (acne, dark spots …) and
      • declared *skin concerns* / *skin type* in preferences
5.  Applies **allergen filtering** (filtering_products.allergen.AllergenFilter)
6.  Calculates weighted scores using the existing
    analysis_recommendation.analysis.ProductAnalysisModule
7.  (Optional) Filters the final list by `product_type` (face, hair, …)

CLI usage
~~~~~~~~~
```
python3 analysis_recommendation/analysis_preference.py --user_id 2 --top_n 5 --alpha 0.8 --verbose
```
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List
import re
import numpy as np



ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ---------------------------------------------------------------------------
# Project imports 
from mapping import BeautyPreferencesSkinConcern, BeautyPreferencesSkinType
from utility.get_preference import get_preference

from analysis_recommendation.analysis import ProductAnalysisModule, display_results
from db.connection import get_database_manager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VECTOR_DIM = 384  # must match pgvector dimension


def _pgvector_to_np(raw: str) -> np.ndarray:
    """Convert pgvector string '[0.1,0.2,...]' to numpy 1-D float array."""
    if raw is None:
        raise ValueError("Null embedding")
    if raw.startswith("[") and raw.endswith("]"):
        return np.fromstring(raw[1:-1], sep=",", dtype=float)
    raise ValueError("Unexpected vector format")


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return 0.0
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    cos = float(np.dot(a, b) / denom)
    # Convert to 0.5-1 scale same as SQL (1 - dist/2)
    return 0.5 + 0.5 * cos


def _tokenize_doc(doc: str) -> set[str]:
    """Tokenise profile doc: split CamelCase and non-alphanumerics to lower-case tokens."""
    camel = re.sub(r"([a-z])([A-Z])", r"\1 \2", doc)
    words = re.sub(r"[^A-Za-z0-9]+", " ", camel).lower().split()
    return set(words)


def _build_pref_vector(prefs: Dict) -> np.ndarray | None:
    """Create centroid vector of tokens mapped to concept embeddings."""
    from user_profile_recommendation.create_user_document import create_user_profile_document

    doc = create_user_profile_document(prefs)
    tokens = _tokenize_doc(doc)
    if not tokens:
        return None

    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT embedding FROM concepts
                    WHERE lower(name) = ANY(%s) AND embedding IS NOT NULL
                    """,
                    (list(tokens),),
                )
                rows = cur.fetchall()
    except Exception:
        rows = []
    if not rows:
        return None
    vecs = [ _pgvector_to_np(r[0]) for r in rows ]
    return np.vstack(vecs).mean(axis=0) if vecs else None

def _warn_if_missing_embedding(user_id: int) -> None:
    """Log a warning if the user does not have an embedding stored in DB.

    This is only a courtesy – ProductAnalysisModule already falls back gracefully
    when the embedding is NULL, but the message helps operators notice the data
    gap without digging through SQL errors.
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT embedding IS NOT NULL FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if not row or not row[0]:
                    print(f"⚠️  Warning: users.embedding not found for user {user_id}; profile similarity will be skipped.")
    except Exception:
        # Connection problems will be handled later by the analysis module
        pass


def _map_pref_concerns(prefs: Dict) -> Dict[str, float]:
    """Convert *skinConcerns* and *skinType* ids → canonical concern names.

    Returns a **dict[concern_name_lower, weight]** (weights currently =1).
    """
    concern_scores: Dict[str, float] = {}

    # --- skin concerns --------------------------------------------------
    for cid in prefs.get("skinConcerns", []):
        cname = BeautyPreferencesSkinConcern.get(cid)
        if cname:
            concern_scores[cname.lower()] = concern_scores.get(cname.lower(), 0.0) + 1.0

    # --- skin type as a pseudo-concern ----------------------------------
    stype_id = prefs.get("skinType")
    if stype_id is not None:
        stype_name = BeautyPreferencesSkinType.get(stype_id)
        if stype_name:
            concern_scores[stype_name.lower()] = concern_scores.get(stype_name.lower(), 0.0) + 1.0

    return concern_scores

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_candidate_products(
    *,
    concern_embeddings: Dict[str, List[float]],
    concern_scores: Dict[str, float],
    allergen_where: str,
    allergen_params: List[str],
    max_price: float | None,
    include_out_of_stock: bool,
    product_type: str | None,
    top_n: int,
) -> List[Dict]:
    """Run a SQL query to get products + concern_score + embedding."""
    if not concern_embeddings:
        return []
    concern_clauses: List[str] = []
    params: List = []
    for cname, emb in concern_embeddings.items():
        weight = concern_scores.get(cname.lower(), 1.0)
        concern_clauses.append("(%s * (1 - (p.embedding <=> %s::vector)))")
        params.extend([weight, str(emb)])
    concern_formula = " + ".join(concern_clauses)
    where = ["p.embedding IS NOT NULL"]
    if not include_out_of_stock:
        where.append("p.stock_status = 0")
    if max_price is not None:
        where.append("p.price <= %s")
        params.append(max_price)
    
    if allergen_where:
        where.append(f"({allergen_where})")
        params.extend(allergen_params)

    where_clause = " AND ".join(where)
    sql = f"""
        SELECT p.id, p.name, p.key_benefits, p.description, p.price, p.stock_status,
               p.embedding, ({concern_formula}) AS concern_score
        FROM products p
        WHERE {where_clause}
        ORDER BY concern_score DESC
        LIMIT %s
    """
    params.append(top_n)
    with get_database_manager().get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    results = []
    for row in rows:
        (pid, name, benefits, desc, price, stock, emb_str, cscore) = row
        results.append({
            "id": pid,
            "name": name,
            "key_benefits": benefits,
            "description": desc,
            "price": float(price) if price else 0.0,
            "stock_status": stock,
            "embedding_str": emb_str,
            "concern_score": float(cscore) if cscore else 0.0,
        })
    return results

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_recommender(
    user_id: int,
    *,
    confidence_threshold: float = 0.5,
    top_n: int = 10,
    max_price: float | None = None,
    include_out_of_stock: bool = False,
    alpha: float = 0.8,
    beta: float | None = None,
    product_type: str | None = None,
    verbose: bool = False,
) -> Dict:
    """High-level orchestration returning the result JSON."""

    # -------------------------------------------------------------------
    # 1) Instantiate analysis module ------------------------------------
    analyzer = ProductAnalysisModule(confidence_threshold=confidence_threshold)

    # Pre-flight: warn if user embedding is missing
    _warn_if_missing_embedding(user_id)

    # Validate weights ---------------------------------------------------
    if beta is None:
        beta = 1.0 - alpha
    if not np.isclose(alpha + beta, 1.0):
        raise ValueError("alpha + beta must equal 1.0")

    # -------------------------------------------------------------------
    # 2) Collect + merge concerns ---------------------------------------
    analysis_rows = analyzer._get_filtered_analysis(user_id)  
    concern_scores = analyzer._map_analysis_to_concerns(analysis_rows)  

    # add preference-derived concerns
    prefs = get_preference(user_id) or {}
    pref_concerns = _map_pref_concerns(prefs)
    for k, v in pref_concerns.items():
        concern_scores[k] = concern_scores.get(k, 0.0) + v

    if verbose:
        print("\n🔎 Combined concern score table:")
        for k, v in concern_scores.items():
            print(f"   {k:<25} {v:.3f}")

    # -------------------------------------------------------------------
    # 3) Embeddings for concerns ----------------------------------------
    concern_embeddings = analyzer._get_concern_embeddings(list(concern_scores.keys()))  # noqa: SLF001

    # -------------------------------------------------------------------
    # 4) Allergen SQL components ----------------------------------------
    allergen_where, allergen_params = analyzer._get_allergen_filter(user_id)  # noqa: SLF001

    # -------------------------------------------------------------------
    # 4b) Preference vector ----------------------------------------------
    pref_vec = _build_pref_vector(prefs)

    # -------------------------------------------------------------------
    # 5) Fetch candidate products ----------------------------------------
    raw_products = _fetch_candidate_products(
        concern_embeddings=concern_embeddings,
        concern_scores=concern_scores,
        allergen_where=allergen_where,
        allergen_params=allergen_params,
        max_price=max_price,
        include_out_of_stock=include_out_of_stock,
        product_type=product_type,
        top_n=top_n * 3,  # fetch extra for better re-ranking
    )

    products: List[Dict] = []
    for p in raw_products:
        try:
            p_vec = _pgvector_to_np(p["embedding_str"])
        except Exception:
            p_vec = None
        pref_sim = _cosine_sim(pref_vec, p_vec) if pref_vec is not None else 0.5
        final_score = alpha * p["concern_score"] + beta * pref_sim
        p.update(
            {
                "pref_score": pref_sim,
                "final_score": final_score,
                "in_stock": p["stock_status"] == 0,
                "concern_scores": {},
            }
        )
        products.append(p)

    # sort & trim
    products.sort(key=lambda x: x["final_score"], reverse=True)
    products = products[:top_n]

    # optional post-filter by product_type (if DB column exists or via keyword match)
    if product_type:
        product_type_lower = product_type.lower()
        products = [
            p
            for p in products
            if (
                p.get("category", "").lower() == product_type_lower
                or product_type_lower in (p.get("name", "").lower())
                or product_type_lower in (p.get("description", "").lower())
            )
        ]

    # -------------------------------------------------------------------
    # 6) Assemble result -------------------------------------------------
    result = {
        "user_id": user_id,
        "analysis_summary": analyzer._create_analysis_summary(analysis_rows, concern_scores),  # noqa: SLF001
        "products": products,
        "parameters": {
            "confidence_threshold": confidence_threshold,
            "top_n": top_n,
            "max_price": max_price,
            "include_out_of_stock": include_out_of_stock,
            "alpha": alpha,
            "beta": beta,
            "product_type": product_type,
        },
    }

    return result

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:  # noqa: D401
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="SmartBeauty integrated recommender")
    parser.add_argument("--user_id", type=int, required=True, help="User ID")
    parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold for analysis")
    parser.add_argument("--top_n", type=int, default=10, help="Number of products to return")
    parser.add_argument("--max_price", type=float, help="Maximum price filter")
    parser.add_argument("--alpha", type=float, default=0.8, help="Weight for concern similarity (0-1)")
    parser.add_argument("--beta", type=float, help="Weight for preference similarity (0-1); defaults to 1-α")
    parser.add_argument("--include_out_of_stock", action="store_true", help="Include out-of-stock items")
    parser.add_argument("--product_type", help="Filter by product type (face, hair, …)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


if __name__ == "__main__":  # pragma: no cover
    args = _parse_args()
    res = run_recommender(
        user_id=args.user_id,
        confidence_threshold=args.threshold,
        top_n=args.top_n,
        max_price=args.max_price,
        include_out_of_stock=args.include_out_of_stock,
        alpha=args.alpha,
        beta=args.beta,
        product_type=args.product_type,
        verbose=args.verbose,
    )

    # pretty print -------------------------------------------------------
    display_results(res, verbose=args.verbose)


