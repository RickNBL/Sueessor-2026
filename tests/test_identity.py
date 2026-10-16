from pathlib import Path

root = Path(__file__).resolve().parents[1]

def test_design_has_history_without_numbered_cards_or_top_bar():
    home = (root/'templates/home.html').read_text()
    base = (root/'templates/base.html').read_text()
    assert '12 de abril de 2002' in home
    assert 'data-heritage-track' in home
    assert 'data-heritage-next' in home
    assert 'service-index' not in home
    assert '<div class="utility">' not in base
    assert 'Portal experimental de redesign' not in base

def test_red_theme_and_typescript_assets_available():
    css = (root/'static/style.css').read_text()
    assert '--brand-red:#ba0a0a' in css
    assert (root/'static/timeline.js').is_file()
    assert (root/'public/static/timeline.js').is_file()
    assert (root/'src/timeline.ts').is_file()
    assert (root/'rust/sueessor-timeline/src/lib.rs').is_file()
