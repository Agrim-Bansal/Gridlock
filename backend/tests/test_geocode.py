"""Geocode lookup tests."""

from app.services.geocode_lookup import _build_display_name


def test_display_name_road_and_locality():
    assert _build_display_name("Outer Ring Road", "Kadubisanahalli") == "Outer Ring Road, Kadubisanahalli"


def test_display_name_unnamed_road():
    assert _build_display_name("Unnamed Road", "Begur Chikkanahalli") == "Begur Chikkanahalli"


def test_display_name_road_only():
    assert _build_display_name("Infantry Road", "") == "Infantry Road"


def test_display_name_locality_only():
    assert _build_display_name("", "Shivaji Nagar") == "Shivaji Nagar"


def test_display_name_empty():
    assert _build_display_name("", "") == ""
    assert _build_display_name("Unnamed Road", "") == ""
