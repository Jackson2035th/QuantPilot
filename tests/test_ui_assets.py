import re
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


def test_landing_page_styles_define_balanced_about_motion_and_mobile_fallback():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    about_rule = stylesheet.split(".landing-about {", 1)[1].split("}", 1)[0]

    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in about_rule
    assert "min-height: 100svh" in about_rule
    assert "scroll-margin-top: 0" in about_rule
    assert ".landing-curve-line" in stylesheet
    assert "animation: landing-curve-draw" not in stylesheet
    assert "@keyframes landing-curve-draw" not in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
    assert ".landing-about { grid-template-columns: 1fr;" in stylesheet


def test_landing_page_reuses_workspace_green_and_animates_a_curve_leading_point():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")
    landing_tokens = stylesheet.split(".landing-page {", 1)[1].split("}", 1)[0]

    assert "--landing-green: var(--color-primary)" in landing_tokens
    assert "--landing-green-dark: var(--color-primary-hover)" in landing_tokens
    assert ".landing-curve-future" in stylesheet
    assert ".landing-curve-glow" in stylesheet
    assert ".landing-curve-point" in stylesheet
    assert "animation: landing-curve-point-pulse" not in stylesheet

    wordmark_rule = stylesheet.split(".landing-wordmark {", 1)[1].split("}", 1)[0]
    about_brand_rule = stylesheet.split(".landing-about-brand {", 1)[1].split("}", 1)[0]
    curve_line_rule = stylesheet.split(".landing-curve-line {", 1)[1].split("}", 1)[0]
    curve_rule = stylesheet.split(".landing-curve {", 1)[1].split("}", 1)[0]

    assert "color: var(--landing-green)" in wordmark_rule
    assert "color: var(--landing-green)" in about_brand_rule
    assert "stroke-width: 3" in curve_line_rule
    assert "bottom: 3.5rem" in curve_rule
    assert "animation:" not in curve_line_rule
    assert ".landing-curve-future.is-visible" in stylesheet


def test_landing_workflow_preview_is_unframed_aligned_and_compact():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    process_rule = stylesheet.split(".landing-process {", 1)[1].split("}", 1)[0]
    step_number_rule = stylesheet.split(".landing-step-number {", 1)[1].split("}", 1)[0]
    preview_rule = stylesheet.split(".landing-workflow-preview {", 1)[1].split("}", 1)[0]
    preview_image_rule = stylesheet.split(".landing-workflow-preview img {", 1)[1].split("}", 1)[0]
    note_rule = stylesheet.split(".landing-workflow-note {", 1)[1].split("}", 1)[0]
    cta_rule = stylesheet.split(".landing-cta {", 1)[1].split("}", 1)[0]

    assert "padding: 4rem 0 2rem" in process_rule
    assert "min-height: 100svh" in process_rule
    assert "scroll-margin-top: 0" in process_rule
    assert "border: 2px solid var(--landing-green)" in step_number_rule
    assert "border:" not in preview_rule
    assert "border-radius:" not in preview_rule
    assert "background:" not in preview_rule
    assert "width: 100%" in preview_rule
    assert "width: 104.35%" in preview_image_rule
    assert "font-size: .82rem" in note_rule
    assert "text-align: center" in note_rule
    assert "transform: translate(-2.49%, -10.5%)" in preview_image_rule
    assert "padding: 2rem 1.5rem 3.5rem" in cta_rule
    assert "margin-top: clamp(2.5rem, 5vh, 4rem)" in cta_rule


def test_mobile_landing_has_navigation_curve_clearance_and_scaled_workflow():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")
    template = Path("templates/landing.html").read_text(encoding="utf-8")

    assert ".landing-mobile-menu" in stylesheet
    assert "grid-template-columns: 1fr auto auto" in stylesheet
    assert "min-width: 64rem" not in stylesheet
    assert ".landing-curve { bottom: 3.5rem; height: 14rem; }" in stylesheet
    assert ".landing-workflow-preview { display: none; }" in stylesheet
    assert ".landing-workflow-mobile {" in stylesheet
    assert "display: grid;" in stylesheet
    assert ".landing-workflow-mobile-crop" in stylesheet
    assert ".landing-workflow-mobile-report-card" in stylesheet
    assert ".landing-workflow-mobile-report-icon" in stylesheet
    assert ".landing-workflow-mobile-metrics" in stylesheet
    assert ".landing-workflow-mobile-idea { width: auto; height: 100%; max-width: 94%;" in stylesheet
    assert ".landing-workflow-mobile-parameters { width: auto; height: 100%; max-width: 100%;" in stylesheet
    assert "grid-template-rows: auto minmax(0, 1fr) auto" in stylesheet
    assert ".landing-workflow-mobile-parameters::after" not in stylesheet
    assert "height: clamp(22rem, 105vw, 25rem)" in stylesheet
    assert "border: 2px solid #a7aeab" in stylesheet
    assert ".landing-workflow-mobile-stage:not(:last-child)::after" in stylesheet
    assert 'class="landing-mobile-menu"' in template
    assert 'class="landing-workflow-mobile"' in template
    assert template.count("quantpilot-workflow.png") == 4


def test_strategy_builder_styles_remove_nested_form_frame_and_surface_examples():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")

    prompt_form_rule = stylesheet.split(".strategy-prompt-form {", 1)[1].split("}", 1)[0]

    assert "padding: 0" in prompt_form_rule
    assert "border: 0" in prompt_form_rule
    assert ".strategy-example-chips" in stylesheet
    assert ".strategy-example-chip" in stylesheet


def test_public_guide_uses_a_wide_layout_and_progressive_grids():
    stylesheet = Path("static/css/app.css").read_text(encoding="utf-8")
    template = Path("templates/base.html").read_text(encoding="utf-8")

    assert ".public-guide-main" in stylesheet
    assert "83rem" in stylesheet
    assert ".guide-topbar-actions" in stylesheet
    assert ".guide-checklist-list" in stylesheet
    assert "@media (min-width: 640px) and (max-width: 900px)" in stylesheet
    assert "request.resolver_match.url_name == 'guide'" in template


def test_templates_delegate_behavior_to_shared_static_javascript():
    templates = list(Path("templates").rglob("*.html"))
    inline_script = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.IGNORECASE)
    inline_handler = re.compile(r"\son(?:click|change|input|submit)=", re.IGNORECASE)

    for template_path in templates:
        template = template_path.read_text(encoding="utf-8")
        assert not inline_script.search(template), template_path
        assert not inline_handler.search(template), template_path

    dashboard = Path("templates/backtests/dashboard.html").read_text(encoding="utf-8")
    result = Path("templates/backtests/result_detail.html").read_text(encoding="utf-8")
    chart_module = Path("static/js/equity-chart.js").read_text(encoding="utf-8")

    assert "js/equity-chart.js" in dashboard
    assert "js/equity-chart.js" in result
    assert dashboard.count("new window.Chart") == 0
    assert result.count("new window.Chart") == 0
    assert chart_module.count("new window.Chart") == 1
    assert "Array.isArray(points)" in chart_module
    assert "afterBuildTicks(scale)" in chart_module
    assert 'font: { size: 14, weight: "600" }' in chart_module

    landing = Path("templates/landing.html").read_text(encoding="utf-8")
    landing_module = Path("static/js/landing.js").read_text(encoding="utf-8")

    assert "js/landing.js" in landing
    assert "requestAnimationFrame" not in landing
    assert "requestAnimationFrame" in landing_module
    assert "renderProgress(progress)" in landing_module
    assert 'path.setAttribute("d", serializePath(visiblePoints))' in landing_module
    assert "const duration = 8000" in landing_module
    for implementation_detail in (
        "const curvePoints",
        "const densityMultiplier = 2",
        "const trendScale = 1.45",
        "const volatilityScale = 1.55",
        "const densifyCurve",
        "const entryPointCount = 28",
        "const extensionPointCount = 40",
        "const solidEndX = 1235",
        "const createEntryPoints",
        "const extendFutureCurve",
        "const handoffIndex",
    ):
        assert implementation_detail in landing_module
