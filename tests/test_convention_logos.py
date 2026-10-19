from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTITIES = (
    ('sindihclor', 'SINDIHCLOR'),
    ('sindhosp', 'SINDHOSP'),
    ('sindhosfil', 'SINDHOSFIL'),
    ('sinamge', 'SINAMGE'),
    ('sinog', 'SINOG'),
    ('sinbfir', 'SINBFIR'),
)


def test_six_entity_logos_present_and_matched():
    template = (ROOT / 'templates' / 'conventions.html').read_text()
    assert 'class="convention-grid"' in template
    assert 'class="convention-card"' in template
    for slug, entity in ENTITIES:
        assert f"('{entity}', '{slug}.png'," in template
        assert (ROOT / 'static' / 'convenios' / f'{slug}.png').is_file()
        assert (ROOT / 'public' / 'static' / 'convenios' / f'{slug}.png').is_file()
    assert 'https://sueessor.org.br/convencoes-coletivas/' in template


def test_responsive_conventions_style():
    css = (ROOT / 'static' / 'style.css').read_text()
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in css
    assert '@media(max-width:620px){.convention-grid{grid-template-columns:1fr' in css
    assert 'object-fit:contain' in css
