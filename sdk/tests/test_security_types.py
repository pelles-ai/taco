"""Tests for SecurityExt v1 auth-flow advertisement fields and the
v1 OAuth flow Pydantic mirrors (``AuthorizationCodeOAuthFlowV1``,
``DeviceCodeOAuthFlow``)."""

from __future__ import annotations

from taco import (
    AuthorizationCodeOAuthFlow,
    AuthorizationCodeOAuthFlowV1,
    DeviceCodeOAuthFlow,
    MutualTLSSecurityScheme,
    SecurityExt,
)


class TestSecurityExtV1Flags:
    def test_defaults_keep_v1_flags_none(self):
        sec = SecurityExt()
        assert sec.mtls_supported is None
        assert sec.pkce_required is None
        assert sec.device_code_supported is None

    def test_serializes_with_camelcase_aliases(self):
        sec = SecurityExt(
            mtls_supported=True,
            pkce_required=True,
            device_code_supported=False,
        )
        dumped = sec.model_dump(by_alias=True, exclude_none=True)
        assert dumped["mtlsSupported"] is True
        assert dumped["pkceRequired"] is True
        assert dumped["deviceCodeSupported"] is False

    def test_round_trip_preserves_v1_flags(self):
        original = SecurityExt(
            trust_tier=2,
            scopes_offered=["taco:trade:mechanical"],
            mtls_supported=True,
            pkce_required=True,
            device_code_supported=True,
        )
        roundtrip = SecurityExt.model_validate_json(original.model_dump_json())
        assert roundtrip.mtls_supported is True
        assert roundtrip.pkce_required is True
        assert roundtrip.device_code_supported is True
        assert roundtrip.trust_tier == 2

    def test_accepts_camelcase_input(self):
        sec = SecurityExt.model_validate(
            {
                "trustTier": 1,
                "mtlsSupported": True,
                "pkceRequired": False,
                "deviceCodeSupported": True,
            }
        )
        assert sec.trust_tier == 1
        assert sec.mtls_supported is True
        assert sec.pkce_required is False
        assert sec.device_code_supported is True

    def test_pre_v1_clients_unaffected(self):
        """A SecurityExt without the new flags serializes identically to 0.3.x."""
        sec = SecurityExt(trust_tier=1, scopes_offered=["taco:task:estimate"])
        dumped = sec.model_dump(by_alias=True, exclude_none=True)
        assert "mtlsSupported" not in dumped
        assert "pkceRequired" not in dumped
        assert "deviceCodeSupported" not in dumped


class TestAuthorizationCodeOAuthFlowV1:
    def test_pkce_required_defaults_to_none(self):
        flow = AuthorizationCodeOAuthFlowV1(
            authorizationUrl="https://idp/authorize",
            tokenUrl="https://idp/token",
            scopes={"read": "read scope"},
        )
        assert flow.pkce_required is None

    def test_pkce_required_serializes_as_camelcase(self):
        flow = AuthorizationCodeOAuthFlowV1(
            authorizationUrl="https://idp/authorize",
            tokenUrl="https://idp/token",
            scopes={"read": "read scope"},
            pkceRequired=True,
        )
        dumped = flow.model_dump(by_alias=True, exclude_none=True)
        assert dumped["pkceRequired"] is True
        assert dumped["authorizationUrl"] == "https://idp/authorize"
        assert dumped["tokenUrl"] == "https://idp/token"

    def test_field_set_superset_of_v03_flow(self):
        """V1 flow has all v0.3 fields plus pkce_required."""
        v03 = AuthorizationCodeOAuthFlow.model_fields.keys()
        v1 = AuthorizationCodeOAuthFlowV1.model_fields.keys()
        assert set(v03).issubset(set(v1))
        assert "pkce_required" in v1


class TestDeviceCodeOAuthFlow:
    def test_basic_construction(self):
        flow = DeviceCodeOAuthFlow(
            deviceAuthorizationUrl="https://idp/device",
            tokenUrl="https://idp/token",
            scopes={"read": "read scope"},
        )
        assert flow.device_authorization_url == "https://idp/device"
        assert flow.token_url == "https://idp/token"
        assert flow.refresh_url is None
        assert flow.scopes == {"read": "read scope"}

    def test_serializes_with_camelcase_aliases(self):
        flow = DeviceCodeOAuthFlow(
            deviceAuthorizationUrl="https://idp/device",
            tokenUrl="https://idp/token",
            refreshUrl="https://idp/refresh",
            scopes={"read": "read scope"},
        )
        dumped = flow.model_dump(by_alias=True, exclude_none=True)
        assert dumped["deviceAuthorizationUrl"] == "https://idp/device"
        assert dumped["tokenUrl"] == "https://idp/token"
        assert dumped["refreshUrl"] == "https://idp/refresh"


class TestMutualTLSSecuritySchemeReexport:
    def test_importable_from_taco_root(self):
        scheme = MutualTLSSecurityScheme(description="DoD CA pinned cert")
        assert scheme.description == "DoD CA pinned cert"
        # SDK fills the discriminator constant
        assert scheme.type == "mutualTLS"
