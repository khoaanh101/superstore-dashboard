"""
test_chart.py — Integration tests for /chart/* endpoints.

Endpoints tested:
  GET  /chart/types      — list all chart types
  GET  /chart            — aggregated chart data with optional filters

Auth:
  All /chart endpoints require a valid Bearer token
  (enforced via Depends(get_current_user) at the router level in main.py).

Coverage:
  1. Auth guard — 401 without token
  2. GET /chart/types — returns a full list of known chart type strings
  3. GET /chart — valid chart_type returns data with correct structure
  4. GET /chart — empty DB returns 200 with empty data list
  5. GET /chart — aggregated values match seeded data
  6. GET /chart — optional filters narrow results
  7. GET /chart — invalid chart_type returns 422
  8. GET /chart — limit parameter is respected
  9. Viewer AND admin tokens both allowed (no RBAC restriction)

Design note:
  All value assertions in sections 4–5 are computed dynamically from the
  seeded_sales fixture via _sum_by(), so tests remain correct regardless
  of what values are in the fixture.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SuperstoreSale, User
from tests.helpers import auth_headers

pytestmark = pytest.mark.asyncio


# ── seed helpers ──────────────────────────────────────────────────────────────


def _make_sale(**overrides) -> SuperstoreSale:
    defaults = dict(
        ship_mode="Standard Class",
        segment="Consumer",
        country="United States",
        city="Los Angeles",
        state="California",
        region="West",
        category="Technology",
        sub_category="Phones",
        sales=100.0,
        quantity=1,
        discount=0.0,
        profit=20.0,
    )
    return SuperstoreSale(**{**defaults, **overrides})


@pytest_asyncio.fixture()
async def seeded_sales(db_session: AsyncSession):
    """Insert a predictable dataset for chart tests."""
    sales = [
        # West - Technology
        _make_sale(region="West",  category="Technology",      sub_category="Phones",      sales=300.0, profit=60.0,  segment="Consumer"),
        # West - Furniture
        _make_sale(region="West",  category="Furniture",       sub_category="Chairs",      sales=200.0, profit=-10.0, segment="Corporate"),
        # East - Technology
        _make_sale(region="East",  category="Technology",      sub_category="Phones",      sales=150.0, profit=30.0,  segment="Consumer"),
        # East - Office Supplies
        _make_sale(region="East",  category="Office Supplies", sub_category="Binders",     sales=100.0, profit=10.0,  segment="Home Office"),
        # South - Technology
        _make_sale(region="South", category="Technology",      sub_category="Accessories", sales=50.0,  profit=5.0,   segment="Consumer"),
        # First Class ship mode
        _make_sale(ship_mode="First Class", region="West", category="Technology",          sales=80.0,  profit=15.0,  segment="Consumer"),
    ]
    for s in sales:
        db_session.add(s)
    await db_session.commit()
    return sales


def _sum_by(
    sales: list[SuperstoreSale],
    group_col: str,
    metric: str,
    filters: dict[str, str] | None = None,
) -> dict[str, float]:
    """
    Compute GROUP BY + SUM aggregation from the fixture list.

    """
    result: dict[str, float] = {}
    for s in sales:
        if filters:
            skip = any(
                str(getattr(s, k, "")).lower() != str(v).lower()
                for k, v in filters.items()
            )
            if skip:
                continue
        group_val = str(getattr(s, group_col))
        metric_val = float(getattr(s, metric))
        result[group_val] = result.get(group_val, 0.0) + metric_val
    return result


def _assert_chart_matches(api_data: list[dict], expected: dict[str, float]) -> None:
    """Assert the API response data dict matches the expected dict."""
    actual = {point["label"]: point["value"] for point in api_data}
    assert set(actual.keys()) == set(expected.keys()), (
        f"Label mismatch.\n  API labels   : {sorted(actual.keys())}\n"
        f"  Expected labels: {sorted(expected.keys())}"
    )
    for label, exp_val in expected.items():
        assert actual[label] == pytest.approx(exp_val), (
            f"Value mismatch for label={label!r}: got {actual[label]}, expected {exp_val}"
        )


# ════════════════════════════════════════════════════════════════
# 1. Auth guard
# ════════════════════════════════════════════════════════════════


async def test_chart_types_requires_auth(client: AsyncClient):
    """GET /chart/types must return 401 if no token."""
    resp = await client.get("/chart/types")
    assert resp.status_code == 401


async def test_chart_data_requires_auth(client: AsyncClient):
    """GET /chart must return 401 if no token."""
    resp = await client.get("/chart?chart_type=sales_by_category")
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════
# 2. GET /chart/types
# ════════════════════════════════════════════════════════════════

EXPECTED_CHART_TYPES = {
    "sales_by_category",
    "sales_by_region",
    "sales_by_segment",
    "sales_by_state",
    "sales_by_ship_mode",
    "profit_by_subcategory",
    "profit_by_category",
}


async def test_list_chart_types(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    """Should return all known chart type strings."""
    resp = await client.get("/chart/types", headers=auth_headers(viewer_token))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert set(data) == EXPECTED_CHART_TYPES


async def test_list_chart_types_admin(
    client: AsyncClient, admin_user: User, admin_token: str
):
    """Admin token should also be accepted."""
    resp = await client.get("/chart/types", headers=auth_headers(admin_token))
    assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════
# 3. GET /chart — structure & empty DB
# ════════════════════════════════════════════════════════════════


async def test_chart_empty_db(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    """With no sales data the endpoint must return 200 with an empty data list."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == "sales_by_category"
    assert body["data"] == []


async def test_chart_response_shape(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """Response must match ChartResponse schema: chart_type + list of {label, value}."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "chart_type" in body
    assert "data" in body
    assert isinstance(body["data"], list)
    for point in body["data"]:
        assert "label" in point
        assert "value" in point
        assert isinstance(point["value"], float)


# ════════════════════════════════════════════════════════════════
# 4. GET /chart — aggregated values (computed from fixture, not hardcoded)
# ════════════════════════════════════════════════════════════════


async def test_sales_by_category_values(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """sales_by_category sums sales per category."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "category", "sales"),
    )


async def test_sales_by_region_values(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """sales_by_region sums sales per region."""
    resp = await client.get(
        "/chart?chart_type=sales_by_region",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "region", "sales"),
    )


async def test_sales_by_segment_values(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """sales_by_segment sums sales per segment."""
    resp = await client.get(
        "/chart?chart_type=sales_by_segment",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "segment", "sales"),
    )


async def test_profit_by_category_values(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """profit_by_category sums profit per category (supports negative values)."""
    resp = await client.get(
        "/chart?chart_type=profit_by_category",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "category", "profit"),
    )


async def test_profit_by_subcategory_values(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """profit_by_subcategory groups by sub_category."""
    resp = await client.get(
        "/chart?chart_type=profit_by_subcategory",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "sub_category", "profit"),
    )


async def test_sales_by_ship_mode_values(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """sales_by_ship_mode sums by ship_mode."""
    resp = await client.get(
        "/chart?chart_type=sales_by_ship_mode",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "ship_mode", "sales"),
    )


# ════════════════════════════════════════════════════════════════
# 5. GET /chart — optional filters
# ════════════════════════════════════════════════════════════════


async def test_chart_filter_by_region(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """Filtering by region should narrow results to that region only."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&region=West",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "category", "sales", filters={"region": "West"}),
    )


async def test_chart_filter_by_category(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """Filtering by category on a non-category chart (e.g. by_region) narrows rows."""
    resp = await client.get(
        "/chart?chart_type=sales_by_region&category=Technology",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "region", "sales", filters={"category": "Technology"}),
    )


async def test_chart_filter_by_segment(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """Filtering by segment should only include matching rows."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&segment=Corporate",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "category", "sales", filters={"segment": "Corporate"}),
    )


async def test_chart_multiple_filters(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """Combining region + category filters must AND the constraints."""
    resp = await client.get(
        "/chart?chart_type=sales_by_segment&region=West&category=Technology",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    _assert_chart_matches(
        resp.json()["data"],
        _sum_by(seeded_sales, "segment", "sales", filters={"region": "West", "category": "Technology"}),
    )


async def test_chart_filter_case_insensitive(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """Filters must be case-insensitive (region=west == region=West)."""
    resp_lower = await client.get(
        "/chart?chart_type=sales_by_category&region=west",
        headers=auth_headers(viewer_token),
    )
    resp_upper = await client.get(
        "/chart?chart_type=sales_by_category&region=West",
        headers=auth_headers(viewer_token),
    )
    assert resp_lower.status_code == 200
    assert resp_upper.status_code == 200
    assert resp_lower.json()["data"] == resp_upper.json()["data"]


async def test_chart_filter_no_match_returns_empty(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """A filter that matches no rows should return 200 with empty data, not 404."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&region=Antarctica",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ════════════════════════════════════════════════════════════════
# 6. GET /chart — limit parameter
# ════════════════════════════════════════════════════════════════


async def test_chart_limit_returns_at_most_n_rows(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """limit=1 should return exactly 1 group."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&limit=1",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


async def test_chart_limit_returns_top_group(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """limit=1 must return the group with the highest aggregate value."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&limit=1",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200
    top_label = resp.json()["data"][0]["label"]
    # The top label must be the one with the highest sum in our fixture
    expected = _sum_by(seeded_sales, "category", "sales")
    best = max(expected, key=lambda k: expected[k])
    assert top_label == best


async def test_chart_limit_max_boundary(
    client: AsyncClient, viewer_user: User, viewer_token: str, seeded_sales
):
    """limit=100 (the API max) should still work fine."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&limit=100",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200


async def test_chart_limit_zero_invalid(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    """limit=0 should be rejected with 422."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&limit=0",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 422


async def test_chart_limit_over_max_invalid(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    """limit=101 exceeds the declared max of 100 and should return 422."""
    resp = await client.get(
        "/chart?chart_type=sales_by_category&limit=101",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 422


# ════════════════════════════════════════════════════════════════
# 7. GET /chart — validation errors
# ════════════════════════════════════════════════════════════════


async def test_chart_invalid_chart_type(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    """An unrecognised chart_type value must return 422 Unprocessable Entity."""
    resp = await client.get(
        "/chart?chart_type=not_a_real_chart",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 422


async def test_chart_missing_chart_type(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    """Omitting the required chart_type query param must return 422."""
    resp = await client.get("/chart", headers=auth_headers(viewer_token))
    assert resp.status_code == 422


# ════════════════════════════════════════════════════════════════
# 8. All chart types smoke test (parametrized)
# ════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("chart_type", list(EXPECTED_CHART_TYPES))
async def test_all_chart_types_return_200(
    client: AsyncClient,
    viewer_user: User,
    viewer_token: str,
    seeded_sales,
    chart_type: str,
):
    """Every chart type listed by /chart/types must be queryable without error."""
    resp = await client.get(
        f"/chart?chart_type={chart_type}",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 200, f"Failed for chart_type={chart_type}: {resp.text}"
    body = resp.json()
    assert body["chart_type"] == chart_type
    assert isinstance(body["data"], list)
