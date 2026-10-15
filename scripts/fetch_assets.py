#!/usr/bin/env python3
"""Restore ignored instrument assets from pinned publisher manifests."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def safe_target(base, relative):
    name = PurePosixPath(relative)
    if name.is_absolute() or '..' in name.parts or not name.parts or '\\' in relative:
        raise ValueError(f'Invalid asset path: {relative}')
    target = base / name
    if not target.resolve().is_relative_to(base.resolve()):
        raise ValueError(f'Asset path escapes its library: {relative}')
    return target


def asset_specs(library, root=ROOT):
    if library == 'band':
        base = root / 'assets/soundfonts/generaluser-gs'
        data = json.loads((base/'SOURCE.json').read_text())
        entries = [dict(path=name, **info) for name,info in data['files'].items()]
    elif library == 'orchestra':
        base = root / 'assets/sfz/vsco-2-ce'
        data = json.loads((base/'SOURCE.json').read_text())
        if not re.fullmatch(r'[a-f0-9]{40}',data['commit']):
            raise ValueError('Orchestra manifest must pin an exact Git commit')
        prefix = 'https://raw.githubusercontent.com/sgossner/VSCO-2-CE/'+data['commit']+'/'
        entries = [dict(info,url=prefix+urllib.parse.quote(info['path'])) for info in data['files']]
    else:
        raise ValueError(f'Unknown library: {library}')
    result=[]
    for info in entries:
        url=urllib.parse.urlsplit(info['url'])
        if url.scheme!='https' or url.netloc!='raw.githubusercontent.com':
            raise ValueError('Asset URL must use the recorded publisher on raw.githubusercontent.com')
        if not re.fullmatch(r'[a-f0-9]{64}',info['sha256']) or not isinstance(info['bytes'],int) or info['bytes']<=0:
            raise ValueError('Asset manifest needs SHA-256 and a positive byte count')
        result.append(dict(info,target=safe_target(base,info['path'])))
    return result


def matches(path, spec):
    if not path.is_file() or path.stat().st_size != spec['bytes']:
        return False
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()==spec['sha256']


def ensure_asset(spec, check=False, repair=False, opener=urllib.request.urlopen):
    target=spec['target']
    if matches(target,spec):
        return 'verified'
    if check:
        raise ValueError(f'Missing or invalid asset: {spec["path"]}')
    if target.exists() and not repair:
        raise ValueError(f'Existing asset differs: {spec["path"]}; inspect it or explicitly use --repair')
    target.parent.mkdir(parents=True,exist_ok=True)
    request=urllib.request.Request(spec['url'],headers={'User-Agent':'soundfont2-music-asset-fetcher'})
    temp=None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,prefix=target.name+'.',suffix='.partial',delete=False) as output:
            temp=Path(output.name)
            with opener(request,timeout=45) as response:
                count=0
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:break
                    count+=len(chunk)
                    if count>spec['bytes']:
                        raise ValueError(f'Download exceeds recorded size: {spec["path"]}')
                    output.write(chunk)
        if not matches(temp,spec):
            raise ValueError(f'Download checksum mismatch: {spec["path"]}')
        temp.replace(target)
        return 'downloaded'
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',choices=('band','orchestra','all'),default='band')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check',action='store_true',help='Verify without downloading or modifying files')
    mode.add_argument('--repair',action='store_true',help='Replace files that fail the recorded checksum')
    parser.add_argument('--jobs',type=int,default=4)
    args=parser.parse_args()
    if not 1<=args.jobs<=8:parser.error('jobs must be between 1 and 8')
    names=('band','orchestra') if args.library=='all' else (args.library,)
    specs=[spec for library in names for spec in asset_specs(library)]
    failures=[];counts={'verified':0,'downloaded':0}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        tasks={pool.submit(ensure_asset,s,args.check,args.repair):s for s in specs}
        for index,future in enumerate(as_completed(tasks),1):
            try:counts[future.result()]+=1
            except Exception as error:failures.append(str(error))
            if index%100==0:print(f'Checked {index}/{len(specs)} assets',flush=True)
    print(json.dumps(dict(library=args.library,total=len(specs),**counts,errors=failures),indent=2))
    return 1 if failures else 0


if __name__=='__main__':
    raise SystemExit(main())
