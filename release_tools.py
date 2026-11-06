"""Import finished binaries, or verify an offline signature before publishing them."""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import urllib.parse
import urllib.request
import zipfile

PUBLIC_KEY = '18f63aa46547e93033e5004d033b739547de92d23f6436ca017744dc892d53f7'
FILES = {'FolderLoop-app.zip', 'FolderLoop-runtime.zip', 'unsigned-update.json'}


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        while data := source.read(1024 * 1024):
            result.update(data)
    return result.hexdigest()


def import_build():
    url, expected = os.environ['SOURCE_URL'], os.environ['EXPECTED_SHA256']
    parsed = urllib.parse.urlsplit(url)
    assert parsed.scheme == 'https' and parsed.hostname.endswith('.oaiusercontent.com') and not parsed.username
    assert re.fullmatch('[0-9a-f]{64}', expected)
    total = 0
    with urllib.request.urlopen(url, timeout=60) as source, open('bundle.zip', 'wb') as output:
        while block := source.read(1024 * 1024):
            total += len(block)
            assert total <= 1024 ** 3
            output.write(block)
    assert digest('bundle.zip') == expected, 'Artifact checksum mismatch'
    root = Path('packages')
    root.mkdir()
    with zipfile.ZipFile('bundle.zip') as archive:
        assert len(archive.infolist()) == 3 and set(archive.namelist()) == FILES
        for item in archive.infolist():
            assert item.file_size < 1024 ** 3
            archive.extract(item, root)
    Path('pending-update.json').write_bytes((root / 'unsigned-update.json').read_bytes())
    Path('import.json').write_text(json.dumps({'run_id': int(os.environ['GITHUB_RUN_ID']), 'sha256': expected}))
    print('Imported tested binary packages. Waiting for the separate signed manifest before release.')


def verify():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    envelope = json.loads(Path('update.json').read_bytes())
    payload = base64.b64decode(envelope['payload'], validate=True)
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY)).verify(base64.b64decode(envelope['signature'], validate=True), payload)
    assert payload == Path('packages/unsigned-update.json').read_bytes(), 'Signature is for a different build'
    manifest = json.loads(payload)
    version = manifest['version']
    assert re.fullmatch(r'\d{1,4}\.\d{1,4}(?:\.\d{1,4})?', version)
    assert manifest['format'] == 1 and manifest['platform'] == 'windows-x64'
    names = []
    with zipfile.ZipFile('FolderLoop-Player-Windows-v' + version + '.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as full:
        for group in manifest['groups']:
            asset = group['asset']
            assert asset['name'] in FILES
            path = Path('packages') / asset['name']
            assert path.stat().st_size == asset['size'] and digest(path) == asset['sha256']
            with zipfile.ZipFile(path) as archive:
                assert len(archive.infolist()) == len(group['files']) and set(archive.namelist()) == set(group['files'])
                for item in archive.infolist():
                    name = item.filename
                    parsed = PurePosixPath(name)
                    assert not parsed.is_absolute() and '..' not in parsed.parts and '\\' not in name and ':' not in name
                    info = group['files'][name]
                    assert item.file_size == info['size']
                    result, size = hashlib.sha256(), 0
                    entry = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    with archive.open(item) as source, full.open(entry, 'w') as destination:
                        while block := source.read(1024 * 1024):
                            size += len(block)
                            assert size <= info['size']
                            result.update(block)
                            destination.write(block)
                    assert size == info['size'] and result.hexdigest() == info['sha256']
                    names.append(name)
        assert len(names) == len(set(n.casefold() for n in names))
        full.writestr('.folderloop-managed.json', json.dumps(sorted(names)))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('version=' + version + '\n')
    print('Verified release signature, both packages and every file; full player ZIP is ready.')


if __name__ == '__main__':
    {'import': import_build, 'verify': verify}[sys.argv[1]]()
