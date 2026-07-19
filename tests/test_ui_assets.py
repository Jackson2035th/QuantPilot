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

    assert stylesheet.startswith("* { box-sizing: border-box; }")
    assert ".button-loading" in stylesheet
    assert ".htmx-request .button-loading" in stylesheet


def test_stylesheet_does_not_contain_a_pasted_terminal_command():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    assert "python manage.py" not in stylesheet


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

    assert ":root" in stylesheet
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
