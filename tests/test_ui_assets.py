from pathlib import Path


def test_result_metric_cards_center_their_content():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    metric_card_rule = stylesheet.split(".metric-card {", 1)[1].split("}", 1)[0]

    assert "display: flex" in metric_card_rule
    assert "align-items: center" in metric_card_rule
    assert "justify-content: center" in metric_card_rule
    assert "text-align: center" in metric_card_rule


def test_stylesheet_uses_a_global_box_sizing_reset_and_loading_state():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")
    body_rule = stylesheet.split("body {", 1)[1].split("}", 1)[0]

    assert stylesheet.startswith("* { box-sizing: border-box; }\n")
    assert "python manage.py" not in stylesheet
    assert "--color-page" in body_rule
    assert "--color-surface" in body_rule
    assert ".button-loading" in stylesheet
    assert ".htmx-request .button-loading" in stylesheet


def test_key_templates_keep_lines_short_enough_to_review():
    templates = (
        Path("templates/base.html"),
        Path("templates/backtests/history.html"),
        Path("templates/backtests/partials/parse_result.html"),
    )

    for template in templates:
        assert max(len(line) for line in template.read_text(encoding="utf-8").splitlines()) <= 160


def test_stylesheet_defines_shared_tokens_and_mobile_navigation_states():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    assert stylesheet.count("--color-page:") == 1
    assert "--color-surface" in stylesheet
    assert "--space-page" in stylesheet
    assert ".sidebar-toggle" in stylesheet
    assert ".app-sidebar.is-open" in stylesheet
    assert ".sidebar-backdrop.is-visible" in stylesheet


def test_stylesheet_turns_history_rows_into_cards_on_small_screens():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    assert ".history-table thead { display: none; }" in stylesheet
    assert ".history-table td::before" in stylesheet
    assert "content: attr(data-label);" in stylesheet


def test_password_page_uses_a_structured_password_requirements_alert():
    template = Path("templates/accounts/set_password.html").read_text(encoding="utf-8")
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    assert 'class="password-requirements"' in template
    assert 'data-lucide="shield-check"' in template
    assert "Password requirements" in template
    assert "6+ characters" in template
    assert "Letters + numbers" in template
    assert "{{ description }}" not in template
    assert "{{ form.as_p }}" not in template
    assert 'class="sr-only"' in template
    assert ".password-requirements" in stylesheet
