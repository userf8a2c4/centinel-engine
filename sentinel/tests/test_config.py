import json

import yaml

from scripts import download_and_hash


def test_load_config_reads_yaml_and_env_overrides(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "base_url": "https://example.test/api",
                "timeout": 9,
                "retries": 2,
                "headers": {"User-Agent": "sentinel"},
                "backoff_base_seconds": 2,
                "backoff_max_seconds": 10,
                "candidate_count": 5,
                "required_keys": ["foo"],
                "field_map": {"totals": {"total_votes": ["totales.votos"]}},
                "sources": [
                    {
                        "name": "custom",
                        "department_code": "99",
                        "level": "NAT",
                        "scope": "NATIONAL",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(download_and_hash, "config_path", config_file)
    monkeypatch.delenv("BASE_URL", raising=False)
    monkeypatch.delenv("TIMEOUT", raising=False)
    monkeypatch.delenv("RETRIES", raising=False)
    monkeypatch.setenv("HEADERS", json.dumps({"User-Agent": "override"}))

    config = download_and_hash.load_config()

    assert config["base_url"] == "https://example.test/api"
    assert config["timeout"] == 9.0
    assert config["retries"] == 2
    assert config["headers"]["User-Agent"] == "override"
    assert config["candidate_count"] == 5
    assert config["required_keys"] == ["foo"]
    assert config["sources"][0]["department_code"] == "99"
