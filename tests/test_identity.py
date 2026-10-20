from pathlib import Path

root = Path(__file__).resolve().parents[1]

def test_design_has_history_without_numbered_cards_or_top_bar():
    home = (root/'templates/home.html').read_text()
    base = (root/'templates/base.html').read_text()
    about = (root/'templates/about.html').read_text()
    assert 'data-heritage-track' not in home
    assert 'id="trajetoria"' not in home
    assert 'data-heritage-track' in about
    assert 'data-heritage-next' in about
    assert 'hero-video-player' in home
    assert 'Agora o <span>Sueessor</span> tem aplicativo' in home
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
