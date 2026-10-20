"""Confere os membros do RAR original usando metadados de tamanho e CRC-32."""
from pathlib import Path
import json,zlib

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'static/sinog_archive_manifest.json').read_text())
INDEX=json.loads((ROOT/'static/convention_index.json').read_text())


def test_all_sinog_rar_members_are_available_with_original_names_and_bytes():
    entries=MANIFEST['entries']
    listed={d['filename']:d for g in INDEX['sinog'] for d in g['documents']}
    assert MANIFEST['source_archive']=='sinog.rar'
    assert len(entries)==len(listed)==15
    for member in entries:
        name=member['original_name']
        assert name in listed
        path=ROOT/'public/convencoes/arquivos/sinog'/name
        assert path.is_file()
        assert path.stat().st_size==member['size_bytes']
        checksum=0
        with path.open('rb') as f:
            assert f.read(5)==b'%PDF-'
            f.seek(0)
            for buf in iter(lambda:f.read(1<<20),b''):
                checksum=zlib.crc32(buf,checksum)
        assert f'{checksum:08x}'==member['crc32']
        assert listed[name]['url']==f'/convencoes/arquivos/sinog/{name}'


def test_sinog_card_explicitly_distinguishes_sinbfir_and_the_duplicate():
    entries=MANIFEST['entries']
    assert sum(x['document_identification']=='SINBFIR' for x in entries)==11
    index={d['filename']:d for g in INDEX['sinog'] for d in g['documents']}
    assert sum(len(group['documents']) for group in INDEX['sinog'])==15
    for x in entries:
        if x['document_identification']=='SINBFIR':
            assert 'SINBFIR' in index[x['original_name']]['label']
            assert index[x['original_name']].get('note')
    assert index['3-sinog_2019_2020.pdf']['note']
