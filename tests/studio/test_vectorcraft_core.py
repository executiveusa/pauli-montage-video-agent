import hashlib
import tempfile
import threading
import unittest
from pathlib import Path
from PIL import Image
from tests.studio.vector_fixtures import make_svg
from yappy_clipz.crafts import vectorcraft as v, service
from yappy_clipz.crafts.remote import LocalCraftRunner, RemoteCraftRunner

SPEC = {'title':'Vector', 'input':'ast_x', 'steps':[{'op':'rotate', 'params':{'angle':20}}], 'output':{'format':'svg'}}
class SpecTests(unittest.TestCase):
    def test_spec_and_refusals(self):
        self.assertEqual(v.parse_spec(SPEC), SPEC)
        for spec in [None, {}, {**SPEC,'argv':[]}, {**SPEC,'steps':[]}, {**SPEC,'steps':[{'op':'file.open'}]}, {**SPEC,'output':{'format':'png'}}, {**SPEC,'steps':[{'op':'rotate','params':{'angle':float('nan')}}]}, {**SPEC,'steps':[{'op':'rotate','params':{'angle':True}}]}]:
            with self.assertRaises(v.VectorSpecError): v.parse_spec(spec)
        for op, (_, defs) in v.OPS.items():
            for k,(lo,hi,_) in defs.items():
                for val in (lo,hi): v.parse_spec({**SPEC,'steps':[{'op':op,'params':{k:val}}]})
                for val in (lo-1,hi+1):
                    with self.assertRaises(v.VectorSpecError): v.parse_spec({**SPEC,'steps':[{'op':op,'params':{k:val}}]})
    def test_svg_boundary(self):
        self.assertEqual(v.sniff(make_svg()), ('svg',320,240))
        for data in [b'not svg', make_svg().replace(b'<rect',b'<script'), make_svg().replace(b'<rect',b'<image href="file:///etc/passwd"'), make_svg().replace(b'<rect',b'<rect onclick="x"'), make_svg().replace(b'fill="#ff7040"',b'fill="url(http://evil)"'), b'<!DOCTYPE svg>'+make_svg(), make_svg().replace(b'width="320"',b'width="9999"'), make_svg().replace(b'<rect',b'<use href="#x"'), make_svg().replace(b'<rect',b'<text'), b'x'*(v.MAX_INPUT_BYTES+1)]:
            with self.assertRaises(v.VectorSpecError): v.sniff(data)

@unittest.skipUnless(v.binary_available(), 'set YAPPY_VECTORCRAFT_BIN')
class RunnerTests(unittest.TestCase):
    def test_real_ops_both_exports_local_and_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'work').mkdir()
            srv=service.make_server('127.0.0.1',0,root/'work'); threading.Thread(target=srv.serve_forever,daemon=True).start()
            try:
                for runner in (LocalCraftRunner(root/'scratch'),RemoteCraftRunner(f'http://127.0.0.1:{srv.server_address[1]}')):
                    self.assertTrue(runner.healthy('vectorcraft'))
                    info=runner('vectorcraft','info',inputs=[make_svg()])
                    self.assertEqual(info['documents'][0]['objects'],3)
                    for op in v.OPS:
                        for fmt in ('svg','pdf'):
                            for edge in ('default','lo','hi'):
                                params={} if edge=='default' else {k:r[0 if edge=='lo' else 1] for k,r in v.OPS[op][1].items()}
                                out=root/'out'; spec={**SPEC,'steps':[{'op':op,'params':params}],'output':{'format':fmt}}
                                facts=runner('vectorcraft','build',inputs=[make_svg()],spec=spec,out_dir=out)
                                self.assertEqual(facts['version'],v.PINNED_VERSION)
                                self.assertEqual(facts['sha256'],hashlib.sha256((out/facts['output']).read_bytes()).hexdigest())
                                self.assertEqual(facts['warnings'],[])
                                self.assertEqual(Image.open(out/'previews/after.png').size,(320,240))
            finally: srv.shutdown(); srv.server_close()
    def test_service_refusals_and_input_not_echoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); service.store_input(root,'vectorjob1','in0.svg',make_svg())
            with self.assertRaises(service.ServiceError): service.read_file(root,'vectorjob1','in0.svg')
            with self.assertRaises(service.ServiceError): service.store_input(root,'vectorjob2','in0.svg',b'<svg/>')
            with self.assertRaises(service.ServiceError): service.run(root,{'engine':'vectorcraft','jobId':'vectorjob1','stage':'mcp','inputs':['in0.svg']})
            with self.assertRaises(service.ServiceError): service.run(root,{'engine':'vectorcraft','jobId':'vectorjob1','stage':'build','inputs':['in0.svg'],'spec':{**SPEC,'steps':[{'op':'file.open'}]}})
