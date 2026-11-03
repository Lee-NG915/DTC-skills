import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'skills/nb-project-upload/scripts'
sys.path.insert(0,str(ROOT))
import review_candidates as cli

class CandidateTests(unittest.TestCase):
    def run_cli(self,args,responses):
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.dict(os.environ,{'NB_PROJECT_URL':'https://catalog.example.invalid','NB_PROJECT_INGEST_TOKEN':'fixture-token'}), patch.object(cli,'request',side_effect=responses) as request, contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            code=cli.main(args)
        return code,stdout.getvalue(),stderr.getvalue(),request

    def test_list_and_default_preview_never_write(self):
        code,out,err,req=self.run_cli([], [{'items':[]}])
        self.assertEqual(code,0);self.assertIsNone(req.call_args.kwargs.get('body'))
        with tempfile.NamedTemporaryFile('w',suffix='.json') as f:
            json.dump({'expectedVersion':1,'draft':{'title':'Example'}},f);f.flush()
            code,out,err,req=self.run_cli(['--candidate-id','abc','--input',f.name],[{'item':{'id':'abc','version':1,'status':'new'}}])
        self.assertEqual(code,0);self.assertTrue(json.loads(out)['dryRun']);self.assertEqual(req.call_count,1)

    def test_save_requires_correct_version_and_verifies_exact_draft(self):
        draft={'title':'Example'}
        before={'item':{'id':'abc','version':1,'status':'new'}}
        after={'item':{'id':'abc','version':2,'status':'draft','draft':draft}}
        with tempfile.NamedTemporaryFile('w',suffix='.json') as f:
            json.dump({'expectedVersion':1,'draft':draft},f);f.flush()
            code,out,err,req=self.run_cli(['--candidate-id','abc','--input',f.name,'--save'],[before,after,after])
            self.assertEqual(code,0);self.assertEqual(req.call_count,3);self.assertFalse(json.loads(out)['published'])
            self.assertEqual(req.call_args_list[1].kwargs['body']['expectedVersion'],1)
            code,out,err,req=self.run_cli(['--candidate-id','abc','--input',f.name,'--save'],[after])
            self.assertEqual(code,1);self.assertEqual(req.call_count,1)

    def test_failed_readback_preserves_acknowledged_state(self):
        draft={'title':'Example'}
        with tempfile.NamedTemporaryFile('w',suffix='.json') as f:
            json.dump({'expectedVersion':1,'draft':draft},f);f.flush()
            code,out,err,req=self.run_cli(['--candidate-id','abc','--input',f.name,'--save'],[
                {'item':{'id':'abc','version':1,'status':'new'}},
                {'item':{'id':'abc','version':2,'status':'draft','draft':draft}},cli.UploadError('network')])
        self.assertEqual(code,1);self.assertEqual(json.loads(err)['writeState'],'acknowledged');self.assertEqual(req.call_count,3)

    def test_bad_input_and_identity_are_rejected(self):
        with tempfile.NamedTemporaryFile('w',suffix='.json') as f:
            f.write('{"expectedVersion":1,"expectedVersion":2,"draft":{}}');f.flush()
            with self.assertRaises(cli.UploadError):cli.load_draft(f.name)
        code,out,err,req=self.run_cli(['--candidate-id','../review','--save'],[])
        self.assertEqual(code,1);self.assertEqual(req.call_count,0)

    def test_transport_uses_patch_only_and_refuses_redirect(self):
        from urllib.error import HTTPError
        with patch.object(cli,'build_opener') as opener:
            opener.return_value.open.side_effect=HTTPError('https://example.invalid',302,'secret server detail',{},io.BytesIO(b''))
            with self.assertRaises(cli.UploadError) as caught:cli.request('https://catalog.example.invalid','token','/abc',body={'draft':{}})
            self.assertNotIn('secret',str(caught.exception));self.assertEqual(caught.exception.write_state,'not_started')
            self.assertEqual(opener.return_value.open.call_args.args[0].get_method(),'PATCH')
            self.assertIsInstance(opener.call_args.args[0],cli.NoRedirect)

if __name__=='__main__':unittest.main()
