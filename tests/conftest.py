"""Fail closed before any test can mutate a non-test database."""
import os
import pytest
from sqlalchemy.engine import make_url


@pytest.fixture(autouse=True)
def require_isolated_mysql_test_database():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        return
    try:
        parsed = make_url(url)
    except Exception:
        pytest.fail("TEST_DATABASE_URL tidak valid")
    if parsed.drivername != "mysql+pymysql" or parsed.database != "sentiment_freeport_test":
        pytest.fail("TEST_DATABASE_URL wajib menunjuk MySQL sentiment_freeport_test")
    primary = os.environ.get("DATABASE_URL")
    if primary and make_url(primary).database == parsed.database:
        pytest.fail("DATABASE_URL dan TEST_DATABASE_URL tidak boleh menunjuk database sama")
