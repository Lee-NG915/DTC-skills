#!/usr/bin/env python3
"""Read discovery candidates and save versioned editorial drafts; never approve."""
import http.client
import json
import math
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, build_opener
from upload_projects import (MAX_BYTES, NoRedirect, SafeArgumentParser, UploadError,
                             origin, unique_object, reject_constant)


def request(base, token, path, *, body=None, timeout=20):
    raw = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if raw is not None and len(raw) > MAX_BYTES:
        raise UploadError('Draft exceeds 128 KiB.', phase='input')
    req = Request(base + '/api/ingest/candidates' + path, data=raw,
                  method='GET' if raw is None else 'PATCH',
                  headers={'Authorization': 'Bearer ' + token, 'Content-Type':'application/json',
                           'Accept':'application/json', 'User-Agent':'nb-project-candidates/1.0'})
    phase = 'read' if raw is None else 'save'
    unknown = 'not_started' if raw is None else 'unknown'
    try:
        with build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError('Response too large')
            value = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
            if not isinstance(value, dict):
                raise ValueError('Invalid response')
            return value
    except HTTPError as error:
        status = error.code
        error.close()
        message = 'Version conflict; read the latest candidate and merge without discarding your draft.' if status == 409 else 'Request rejected; check endpoint, credentials and draft contract.'
        state = 'not_started' if status in (400,401,403,404,409,413,415,422) or 300 <= status < 400 else unknown
        raise UploadError(f'HTTP {status}: {message}', phase=phase, write_state=state) from None
    except (ValueError, UnicodeError, URLError, TimeoutError, OSError, http.client.HTTPException):
        raise UploadError('Unconfirmed response; read the candidate before retrying a save.', phase=phase, write_state=unknown) from None


def load_draft(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES: raise ValueError('Too large')
        body = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
        if not isinstance(body, dict) or set(body) != {'expectedVersion','draft'}: raise ValueError('Shape')
        if type(body['expectedVersion']) is not int or body['expectedVersion'] < 1: raise ValueError('Version')
        if not isinstance(body['draft'], dict): raise ValueError('Draft')
        json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
        return body
    except (OSError, ValueError, UnicodeError):
        raise UploadError('Input must be bounded UTF-8 JSON containing expectedVersion and draft.',phase='input') from None


def validate_item(response, candidate_id):
    item = response.get('item')
    if not isinstance(item,dict) or item.get('id') != candidate_id or type(item.get('version')) is not int or item['version'] < 1 or item.get('status') not in ('new','draft','approved','rejected'):
        raise UploadError('Invalid candidate receipt; read again before writing.',phase='verify',write_state='unknown')
    return item


def main(argv=None):
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument('--base-url')
    parser.add_argument('--candidate-id')
    parser.add_argument('--status', choices=['new','draft','approved','rejected'])
    parser.add_argument('--source')
    parser.add_argument('--kind', choices=['project','skill','case','mcp'])
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--input', help='JSON with expectedVersion and draft; without --save only previews')
    parser.add_argument('--save', action='store_true', help='Save draft and read it back; does not publish')
    parser.add_argument('--timeout', type=float, default=20)
    args = parser.parse_args(argv)
    try:
        base = origin(args.base_url or os.environ.get('NB_PROJECT_URL',''))
        token = os.environ.get('NB_PROJECT_INGEST_TOKEN','')
        if not token or any(c.isspace() or ord(c)<33 or ord(c)>126 for c in token):
            raise UploadError('Set the dedicated NB_PROJECT_INGEST_TOKEN via the environment.')
        if not math.isfinite(args.timeout) or not 0 < args.timeout <= 120 or args.page < 1:
            raise UploadError('Invalid timeout or page.')
        if args.candidate_id and not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',args.candidate_id):
            raise UploadError('Invalid candidate ID.')
        if (args.input or args.save) and not args.candidate_id or args.save and not args.input:
            raise UploadError('Saving requires candidate-id and input.')
        path = '/' + quote(args.candidate_id,safe='') if args.candidate_id else '?' + urlencode({k:v for k,v in {'status':args.status,'kind':args.kind,'sourceId':args.source,'page':args.page,'pageSize':20}.items() if v is not None})
        current = request(base,token,path,timeout=args.timeout)
        if args.candidate_id: validate_item(current,args.candidate_id)
        elif not isinstance(current.get('items'),list): raise UploadError('Invalid candidate list response.',phase='read')
        if args.input:
            body = load_draft(args.input)
            if current['item']['version'] != body['expectedVersion']:
                raise UploadError('Version conflict; fetch and merge the latest candidate.',phase='preflight')
            if not args.save:
                current = {'target':base,'dryRun':True,**body,'published':False}
            else:
                saved = validate_item(request(base,token,path,body=body,timeout=args.timeout), args.candidate_id)
                if saved['version'] != body['expectedVersion'] + 1 or saved.get('status') != 'draft' or saved.get('draft') != body['draft']:
                    raise UploadError('Unconfirmed draft save; read and reconcile before retrying.',phase='verify',write_state='unknown')
                try:
                    readback = validate_item(request(base,token,path,timeout=args.timeout),args.candidate_id)
                    if readback['version'] != saved['version'] or readback.get('draft') != saved.get('draft'): raise ValueError('Changed')
                except (UploadError,ValueError):
                    raise UploadError('Save acknowledged; current draft differs or readback failed. Read and reconcile.',phase='verify',write_state='acknowledged') from None
                current = {'target':base,'item':readback,'verified':True,'published':False}
        print(json.dumps(current,ensure_ascii=False,indent=2))
        return 0
    except UploadError as error:
        print(json.dumps({'ok':False,'error':str(error),'phase':error.phase,'writeState':error.write_state}),file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
