from app.unifi_client import HostSpec, UnifiClient, normalize_base_url


def test_normalize_bare_ip_gets_https_prefix():
    assert normalize_base_url("192.168.1.1") == "https://192.168.1.1"


def test_normalize_keeps_existing_scheme():
    assert normalize_base_url("http://192.168.1.1/") == "http://192.168.1.1"


def test_uckp_path_and_header():
    client = UnifiClient(HostSpec(host_type="uckp", base_url="https://192.168.45.38", credential="mykey"))
    assert client._root() == "https://192.168.45.38"
    assert client._prefix() == "/proxy/access/integration/v1/developer"
    assert client._headers()["X-API-KEY"] == "mykey"
    assert "Authorization" not in client._headers()


def test_unvr_path_and_header_adds_port():
    client = UnifiClient(HostSpec(host_type="unvr", base_url="https://192.168.20.237", credential="mytoken"))
    assert client._root() == "https://192.168.20.237:12445"
    assert client._prefix() == "/api/v1/developer"
    assert client._headers()["Authorization"] == "Bearer mytoken"


def test_unvr_base_url_with_port_already_present_not_duplicated():
    client = UnifiClient(HostSpec(host_type="unvr", base_url="https://192.168.20.237:12445", credential="t"))
    assert client._root() == "https://192.168.20.237:12445"


def test_unknown_host_type_rejected():
    import pytest
    with pytest.raises(ValueError):
        UnifiClient(HostSpec(host_type="udm-pro-weird", base_url="https://x", credential="t"))
