import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.vendor_map import VENDOR_MAP, get_vendors_for_domains


EXPECTED_DOMAINS = [
    "observability_monitoring", "auth_identity_sso", "messaging_event_streaming",
    "data_pipeline_etl", "cicd_devops", "database_data_storage", "security_compliance",
    "search", "feature_flags", "api_gateway_service_mesh", "testing_qa",
    "infrastructure_iac", "cdn_edge_networking", "payments_billing", "notifications_comms",
    "ml_ai_platform", "analytics_bi", "support_ticketing", "ecommerce",
    "marketing_communications",
]


class TestVendorMap:
    def test_all_20_domains_present(self):
        for domain in EXPECTED_DOMAINS:
            assert domain in VENDOR_MAP, f"Missing domain: {domain}"

    def test_no_extra_domains(self):
        assert set(VENDOR_MAP.keys()) == set(EXPECTED_DOMAINS)

    def test_each_domain_has_at_least_one_vendor(self):
        for domain, vendors in VENDOR_MAP.items():
            assert len(vendors) >= 1, f"{domain} has no vendors"

    def test_each_vendor_has_required_fields(self):
        for domain, vendors in VENDOR_MAP.items():
            for v in vendors:
                assert "name" in v, f"{domain}: vendor missing 'name'"
                assert "url" in v, f"{domain}: vendor missing 'url'"
                assert "pitch" in v, f"{domain}: vendor missing 'pitch'"

    def test_vendor_urls_are_non_empty_strings(self):
        for domain, vendors in VENDOR_MAP.items():
            for v in vendors:
                assert isinstance(v["url"], str) and v["url"].startswith("https://"), \
                    f"{domain} / {v['name']}: invalid URL '{v['url']}'"

    def test_feedonomics_in_ecommerce(self):
        names = [v["name"] for v in VENDOR_MAP["ecommerce"]]
        assert "Feedonomics" in names

    def test_glean_in_search(self):
        names = [v["name"] for v in VENDOR_MAP["search"]]
        assert "Glean" in names


class TestGetVendorsForDomains:
    def test_returns_vendors_for_high_confidence(self):
        signals = [{"domain": "observability_monitoring", "confidence": "high", "reasoning": "Prometheus added."}]
        result = get_vendors_for_domains(signals)
        assert len(result) == 1
        assert result[0]["domain"] == "observability_monitoring"
        assert len(result[0]["vendors"]) > 0

    def test_returns_vendors_for_medium_confidence(self):
        signals = [{"domain": "search", "confidence": "medium", "reasoning": "Some search work."}]
        result = get_vendors_for_domains(signals)
        assert len(result) == 1

    def test_excludes_low_confidence(self):
        signals = [{"domain": "search", "confidence": "low", "reasoning": "Minor search hint."}]
        result = get_vendors_for_domains(signals)
        assert result == []

    def test_excludes_unknown_domain(self):
        signals = [{"domain": "not_a_real_domain", "confidence": "high", "reasoning": "..."}]
        result = get_vendors_for_domains(signals)
        assert result == []

    def test_mixed_confidence_filters_correctly(self):
        signals = [
            {"domain": "observability_monitoring", "confidence": "high", "reasoning": "..."},
            {"domain": "search", "confidence": "low", "reasoning": "..."},
            {"domain": "auth_identity_sso", "confidence": "medium", "reasoning": "..."},
        ]
        result = get_vendors_for_domains(signals)
        domains = [r["domain"] for r in result]
        assert "observability_monitoring" in domains
        assert "auth_identity_sso" in domains
        assert "search" not in domains

    def test_result_includes_reasoning(self):
        signals = [{"domain": "payments_billing", "confidence": "high", "reasoning": "Stripe integration added."}]
        result = get_vendors_for_domains(signals)
        assert result[0]["reasoning"] == "Stripe integration added."

    def test_empty_signals_returns_empty(self):
        assert get_vendors_for_domains([]) == []

    def test_org_filter_removes_self_referential_vendor(self):
        # Vercel Edge Network URL contains "vercel" — should be filtered when org="vercel"
        signals = [{"domain": "cdn_edge_networking", "confidence": "high", "reasoning": "CDN work."}]
        result = get_vendors_for_domains(signals, org="vercel")
        vendor_names = [v["name"] for v in result[0]["vendors"]]
        assert "Vercel Edge Network" not in vendor_names

    def test_org_filter_keeps_other_vendors(self):
        # Other cdn vendors should still be present
        signals = [{"domain": "cdn_edge_networking", "confidence": "high", "reasoning": "CDN work."}]
        result = get_vendors_for_domains(signals, org="vercel")
        vendor_names = [v["name"] for v in result[0]["vendors"]]
        assert "Cloudflare" in vendor_names
        assert "Fastly" in vendor_names

    def test_org_filter_is_case_insensitive(self):
        signals = [{"domain": "cdn_edge_networking", "confidence": "high", "reasoning": "CDN work."}]
        result_lower = get_vendors_for_domains(signals, org="vercel")
        result_upper = get_vendors_for_domains(signals, org="Vercel")
        assert result_lower == result_upper

    def test_org_filter_empty_string_no_filtering(self):
        signals = [{"domain": "cdn_edge_networking", "confidence": "high", "reasoning": "CDN work."}]
        all_vendors = get_vendors_for_domains(signals)
        filtered = get_vendors_for_domains(signals, org="")
        assert all_vendors == filtered
