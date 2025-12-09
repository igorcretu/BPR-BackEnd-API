"""Tests for request validation utilities."""
import pytest
from app.utils.request_validation import (
    get_pagination_params,
    parse_json_body,
    validate_year,
    validate_non_negative_number,
    validate_positive_number,
)
from flask import Flask
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request


class TestPaginationParams:
    """Test pagination parameter extraction."""
    
    def test_get_pagination_params_defaults(self):
        """Test pagination with default values."""
        args = {}
        params = get_pagination_params(args)
        assert params.page == 1
        assert params.per_page == 20
    
    def test_get_pagination_params_custom(self):
        """Test pagination with custom values."""
        args = {'page': '3', 'per_page': '50'}
        params = get_pagination_params(args)
        assert params.page == 3
        assert params.per_page == 50
    
    def test_get_pagination_params_max_per_page(self):
        """Test pagination respects max_per_page."""
        args = {'page': '1', 'per_page': '200'}
        params = get_pagination_params(args, max_per_page=100)
        assert params.page == 1
        assert params.per_page == 100
    
    def test_get_pagination_params_invalid_page(self):
        """Test pagination with invalid page number."""
        args = {'page': '0'}
        with pytest.raises(ValueError, match="page must be a positive integer"):
            get_pagination_params(args)
    
    def test_get_pagination_params_invalid_per_page(self):
        """Test pagination with invalid per_page number."""
        args = {'per_page': '-5'}
        with pytest.raises(ValueError, match="per_page must be a positive integer"):
            get_pagination_params(args)
    
    def test_get_pagination_params_non_numeric(self):
        """Test pagination with non-numeric values falls back to defaults."""
        args = {'page': 'abc', 'per_page': 'xyz'}
        params = get_pagination_params(args)
        # Should fall back to defaults
        assert params.page == 1
        assert params.per_page == 20


class TestParseJsonBody:
    """Test JSON body parsing."""
    
    def test_parse_json_body_valid(self):
        """Test parsing valid JSON body."""
        app = Flask(__name__)
        with app.test_request_context(
            '/',
            method='POST',
            data='{"key": "value"}',
            content_type='application/json'
        ):
            from flask import request
            result = parse_json_body(request)
            assert result == {'key': 'value'}
    
    def test_parse_json_body_invalid(self):
        """Test parsing invalid JSON body."""
        app = Flask(__name__)
        with app.test_request_context(
            '/',
            method='POST',
            data='not json',
            content_type='text/plain'
        ):
            from flask import request
            with pytest.raises(ValueError, match="Request body must be valid JSON"):
                parse_json_body(request)
    
    def test_parse_json_body_required_fields(self):
        """Test parsing JSON body with required fields."""
        app = Flask(__name__)
        with app.test_request_context(
            '/',
            method='POST',
            data='{"brand": "Toyota"}',
            content_type='application/json'
        ):
            from flask import request
            with pytest.raises(ValueError, match="Missing required fields: model, year"):
                parse_json_body(request, required_fields=['brand', 'model', 'year'])


class TestValidateYear:
    """Test year validation."""
    
    def test_validate_year_valid(self):
        """Test validating a valid year."""
        validate_year(2020)  # Should not raise
    
    def test_validate_year_too_old(self):
        """Test validating a year that's too old."""
        with pytest.raises(ValueError, match="Year must be between"):
            validate_year(1800, earliest=1900)
    
    def test_validate_year_too_future(self):
        """Test validating a year that's too far in future."""
        with pytest.raises(ValueError, match="Year must be between"):
            validate_year(2100, allow_future_years=1)
    
    def test_validate_year_not_integer(self):
        """Test validating a non-integer year."""
        with pytest.raises(ValueError, match="Year must be an integer"):
            validate_year("2020")


class TestValidateNumbers:
    """Test number validation functions."""
    
    def test_validate_non_negative_number_valid(self):
        """Test validating a valid non-negative number."""
        validate_non_negative_number('mileage', 0)  # Should not raise
        validate_non_negative_number('mileage', 50000)  # Should not raise
    
    def test_validate_non_negative_number_negative(self):
        """Test validating a negative number."""
        with pytest.raises(ValueError, match="mileage cannot be negative"):
            validate_non_negative_number('mileage', -100)
    
    def test_validate_non_negative_number_none(self):
        """Test validating None value."""
        with pytest.raises(ValueError, match="mileage is required"):
            validate_non_negative_number('mileage', None)
    
    def test_validate_positive_number_valid(self):
        """Test validating a valid positive number."""
        validate_positive_number('price', 100000)  # Should not raise
    
    def test_validate_positive_number_zero(self):
        """Test validating zero."""
        with pytest.raises(ValueError, match="price must be greater than zero"):
            validate_positive_number('price', 0)
    
    def test_validate_positive_number_negative(self):
        """Test validating a negative number."""
        with pytest.raises(ValueError, match="price must be greater than zero"):
            validate_positive_number('price', -50000)
    
    def test_validate_positive_number_none(self):
        """Test validating None value."""
        with pytest.raises(ValueError, match="price is required"):
            validate_positive_number('price', None)
