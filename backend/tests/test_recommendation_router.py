from types import SimpleNamespace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient

from app import constants as c
from app.db import get_db
from app.recommendation import router, builder
from app.schemas import RecommendationIn


@pytest.fixture
def setup(monkeypatch):
    db = Mock()
    assessment = SimpleNamespace(id=uuid4(), user_id='test', currency='USD', exclusions=[],
                                 invest_amount=Decimal('10000'), monthly_amount=Decimal('500'), max_loss='5')
    result = SimpleNamespace(id=uuid4(), level=1)
    monkeypatch.setattr(router, 'latest_result', lambda *a: (assessment, result))
    monkeypatch.setattr(router, 'recommendation_of', lambda *a: None)
    return db


@pytest.mark.parametrize('max_loss,reason', [('5', 'no_data'), ('0', 'zero_loss')])
def test_cash_result_is_returned_and_saved_without_allocation_error(setup, monkeypatch, max_loss, reason):
    assessment, result = router.latest_result(setup, 'test')
    assessment.max_loss = max_loss
    monkeypatch.setattr(builder, 'get_price_history', lambda *a, **kw: None)
    def created(record):
        record.created_at = datetime.now(timezone.utc)
    setup.add.side_effect = created
    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[get_db] = lambda: setup
    with TestClient(app) as client:
        response = client.post('/api/v1/recommendation', json={'user_id': 'test'})
    assert response.status_code == 201
    data = response.json()
    assert data['metrics']['reason'] == reason
    assert data['metrics']['volatility_pct'] is None
    assert data['holdings'][0]['ticker'] is None
    assert data['holdings'][0]['amount'] == 10000
    setup.commit.assert_called_once()


def test_old_get_is_not_presented_as_valid_new_allocation(setup, monkeypatch):
    monkeypatch.setattr(router, 'recommendation_of', lambda *a: SimpleNamespace(rules_version='1.2.0'))
    with pytest.raises(HTTPException) as error:
        router.get_recommendation('test', setup)
    assert error.value.status_code == 409
    assert error.value.detail == c.OUTDATED_RECOMMENDATION


def test_old_post_rebuilds_existing_record(setup, monkeypatch):
    existing = SimpleNamespace(id='existing-id', rules_version='1.2.0', holdings=['old'], portfolio={})
    fresh = SimpleNamespace(rules_version='1.4.0', holdings=['new'], portfolio={'volatility_pct': 5}, universe_as_of='2026-09-16')
    monkeypatch.setattr(router, 'recommendation_of', lambda *a: existing)
    monkeypatch.setattr(router, 'build', Mock(return_value=fresh))
    monkeypatch.setattr(router, 'to_out', lambda r, *a: r)
    result = router.create_recommendation(RecommendationIn(user_id='test'), Response(), setup)
    assert result is existing
    assert result.id == 'existing-id'
    assert result.holdings == ['new']
    assert result.rules_version == '1.4.0'
    setup.add.assert_called_once_with(existing)
    setup.commit.assert_called_once()


def test_current_post_remains_idempotent(setup, monkeypatch):
    existing = SimpleNamespace(rules_version='1.4.0', portfolio={'reason': 'optimized'})
    monkeypatch.setattr(router, 'recommendation_of', lambda *a: existing)
    build = Mock()
    monkeypatch.setattr(router, 'build', build)
    monkeypatch.setattr(router, 'to_out', lambda r, *a: r)
    response = Response()
    assert router.create_recommendation(RecommendationIn(user_id='test'), response, setup) is existing
    assert response.status_code == 200
    build.assert_not_called()
    setup.commit.assert_not_called()


@pytest.mark.parametrize('reason', ['no_data', 'optimizer_failed', 'cash_adjusted'])
def test_temporary_or_legacy_result_can_be_rebuilt(setup, monkeypatch, reason):
    existing = SimpleNamespace(rules_version='1.4.0', portfolio={'reason': reason})
    fresh = SimpleNamespace(rules_version='1.4.0', holdings=['new'], portfolio={'reason': 'optimized'}, universe_as_of='2026-09-16')
    monkeypatch.setattr(router, 'recommendation_of', lambda *a: existing)
    build = Mock(return_value=fresh)
    monkeypatch.setattr(router, 'build', build)
    monkeypatch.setattr(router, 'to_out', lambda r, *a: r)
    result = router.create_recommendation(RecommendationIn(user_id='test'), Response(), setup)
    build.assert_called_once()
    assert result.portfolio['reason'] == 'optimized'
