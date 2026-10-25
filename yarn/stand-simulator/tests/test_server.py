import json,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from yarnstand.server import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join(timeout=5);cls.server.server_close()

    def post(self,data,origin=None):
        headers={'Content-Type':'application/json','Origin':origin or self.base}
        return urlopen(Request(self.base+'/simulate',data=json.dumps(data).encode(),headers=headers),timeout=5)

    def test_deep_link_serves_page_and_script(self):
        with urlopen(self.base+'/?stand=peach_v13',timeout=5) as r:
            body=r.read().decode()
        self.assertIn('<script src="/ui.js">',body)
        self.assertIn('value="pitaya_v09"',body)
        with urlopen(self.base+'/ui.js',timeout=5) as r:
            self.assertIn('javascript',r.headers['Content-Type'])
            self.assertIn('function writeControls',r.read().decode())

    def test_both_presets_and_legacy_keys_available(self):
        with urlopen(self.base+'/presets',timeout=5) as r:data=json.load(r)
        for prefix in ['', 'peach_v13/', 'pitaya_v09/', 'lemon_v05/']:
            self.assertIn(prefix+'full/knitting/desk_side',data)

    def test_assets_are_english_by_default_and_for_legacy_language_links(self):
        for query in ['', '?stand=lemon_v05', '?stand=lemon_v05&lang=en', '?lang=ru', '?lang=unknown']:
            with self.subTest(query=query):
                with urlopen(self.base+'/'+query,timeout=5) as r:page=r.read().decode()
                self.assertIn('lang="en"',page)
                self.assertIn('src="/ui.js"',page)
                self.assertIn('Lemon · v05',page)
                self.assertIn('How a yarn stand feeds yarn',page)
                self.assertNotIn('id="language"',page)
                self.assertNotRegex(page,r'[\u0400-\u052f]')
                with urlopen(self.base+'/ui.js'+query,timeout=5) as r:script=r.read().decode()
                self.assertNotRegex(script,r'[\u0400-\u052f]')
                self.assertIn('All displayed forces are conditional',script)
                self.assertIn('The later curve is hypothetical',script)
                self.assertIn('N, hypothetical model peak',script)

    def test_lemon_preset_matches_audited_input_snapshot(self):
        fixture=json.loads((Path(__file__).parents[1]/'examples/lemon_v05.json').read_text(encoding='utf-8'))
        with urlopen(self.base+'/presets',timeout=5) as r:data=json.load(r)
        self.assertEqual(data['lemon_v05/full/knitting/desk_side'],fixture)
        with self.post(fixture) as r:result=json.load(r)
        self.assertTrue(result['summary']['hypotheses_valid_for_entire_run'])
        self.assertAlmostEqual(result['summary']['peak_tension_N'],.08721009604863335,places=10)
        self.assertAlmostEqual(result['summary']['max_rpm'],35.29786693219291,places=9)

    def test_partial_json_is_returned_as_complete_validated_input(self):
        with self.post({'stand':{'mass_kg':.4123},'motion':{'duration_s':2}}) as r:data=json.load(r)
        self.assertEqual(data['inputs']['stand']['mass_kg'],.4123)
        self.assertIn('ball',data['inputs'])
        self.assertIn('peak_tension_before_first_event_N',data['summary'])

    def test_bad_name_returns_json_error(self):
        with self.assertRaises(HTTPError) as error:self.post({'stand':{'name':None}})
        self.assertEqual(error.exception.code,400)
        self.assertIn('name',json.load(error.exception)['error'])

    def test_cross_origin_rejected(self):
        with self.assertRaises(HTTPError) as error:self.post({},'https://example.invalid')
        self.assertEqual(error.exception.code,403)
