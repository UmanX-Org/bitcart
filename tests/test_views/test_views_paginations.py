from datetime import timedelta
from urllib.parse import quote

from starlette.testclient import TestClient

from api import utils
from tests.helper import create_invoice, create_product, create_token, create_user


def test_multiple_query(client: TestClient, token: str):
    user1 = create_user(client)
    user2 = create_user(client)
    query = f"{user1['email']}|{user2['email']}"
    resp = client.get(f"/users?multiple=true&query={query}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


def test_next_prev_url(client: TestClient, token: str):
    # create multiple users
    create_user(client)
    create_user(client)
    resp = client.get("/users?limit=1", headers={"Authorization": f"Bearer {token}"})
    next_url = resp.json()["next"]
    assert next_url.endswith("/users?limit=1&offset=1")
    # previous
    resp = client.get("/users?limit=1&offset=1", headers={"Authorization": f"Bearer {token}"})
    prev_url = resp.json()["previous"]
    assert prev_url.endswith("/users?limit=1")
    # next
    resp = client.get("/users?limit=1&offset=2", headers={"Authorization": f"Bearer {token}"})
    prev_url = resp.json()["previous"]
    assert prev_url.endswith("/users?limit=1&offset=1")


def test_undefined_sort(client: TestClient, token: str):
    resp = client.get("/users?sort=fake", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["result"] == []


def test_products_pagination(client: TestClient, user, token: str):
    product = create_product(client, user["id"], token)
    resp = client.get(
        f"/products?store={product['store_id']}&category={product['category']}&\
            min_price=0.001&max_price={product['price']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["count"] > 0


def test_token_pagination(client: TestClient, user):
    token_data = create_token(client, user, app_id="998")
    permissions = ",".join(token_data["permissions"])
    resp = client.get(
        f"/token?app_id={token_data['app_id']}&redirect_url={token_data['redirect_url']}&permissions={permissions}",
        headers={"Authorization": f"Bearer {token_data['id']}"},
    )
    assert resp.json()["count"] == 1


def check_query(client: TestClient, token: str, column, value, expected_count, allow_nonexisting=False):
    query = quote(f"{column}:{value}")
    resp = client.get(f"/invoices?query={query}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["count"] == expected_count
    if not allow_nonexisting:
        for item in resp.json()["result"]:
            assert item[column] == value


def test_columns_queries(client: TestClient, user, token):
    create_invoice(client, user["id"], token, currency="USD")
    create_invoice(client, user["id"], token, currency="EUR")
    check_query(client, token, "currency", "USD", 1)
    check_query(client, token, "currency", "EUR", 1)


def test_undefined_column_query(client: TestClient, user, token):
    create_invoice(client, user["id"], token, currency="test")
    check_query(client, token, "test", "test", 1, allow_nonexisting=True)  # skips undefined columns


def test_bad_type_column_query(client: TestClient, user, token):
    create_invoice(client, user["id"], token, price=10)
    check_query(client, token, "price", "test", 0)


def check_start_date_query(client, token, date, expected_count, first_id, start=True):
    query = quote(f"start_date:{date}") if start else quote(f"end_date:{date}")
    ind = 0 if start else -1
    resp = client.get(f"/invoices?query={query}&sort=created&desc=false", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["count"] == expected_count
    assert resp.json()["result"][ind]["id"] == first_id


def test_date_pagination(client: TestClient, user, token):
    now = utils.time.now()
    invoice1 = create_invoice(client, user["id"], token, created=(now - timedelta(hours=1)).isoformat())
    invoice2 = create_invoice(client, user["id"], token, created=(now - timedelta(days=1)).isoformat())
    invoice3 = create_invoice(client, user["id"], token, created=(now - timedelta(weeks=1)).isoformat())
    check_start_date_query(client, token, "-2h", 1, invoice1["id"])
    check_start_date_query(client, token, "-2d", 2, invoice2["id"])
    check_start_date_query(client, token, "-2w", 3, invoice3["id"])
    check_start_date_query(client, token, "-1w", 1, invoice3["id"], start=False)
    check_start_date_query(client, token, "-1d", 2, invoice2["id"], start=False)
    check_start_date_query(client, token, "-1h", 3, invoice1["id"], start=False)
