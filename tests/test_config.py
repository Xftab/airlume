from airlume.config import Settings, check_secrets, mask


def _s(**kw):
    base = dict(env="development", db_path="x", use_fake_data=True, groq_api_key="",
                google_ai_api_key="", openaq_api_key="", waqi_token="", carto_api_key="")
    base.update(kw)
    return Settings(**base)


def test_missing_required():
    assert check_secrets(_s(), required=("groq_api_key",)) == ["GROQ_API_KEY is not set (put it in .env)"]


def test_placeholder_detected():
    assert "placeholder" in check_secrets(_s(groq_api_key="your_key_here"), required=("groq_api_key",))[0]


def test_fake_data_blocked_in_prod():
    assert any("production" in p for p in check_secrets(_s(env="production")))


def test_mask():
    assert mask("gsk_abcdef1234") == "**********1234" and mask("") == "(empty)"
