import tempfile
import unittest
from pathlib import Path
from check_public import scan_text, scan_tree

class PublicContentTests(unittest.TestCase):
    def rules(self, text, terms=()):
        return {rule for _, rule in scan_text(text, terms)}

    def test_token(self):
        self.assertIn('token', self.rules('gh' + 'p_' + 'A' * 36))

    def test_key(self):
        self.assertIn('private-key', self.rules('-----BEGIN ' + 'PRIVATE KEY-----'))

    def test_identity_and_path(self):
        self.assertIn('private-deny-term', self.rules('acme-private', ('Acme-Private',)))
        self.assertIn('home-path', self.rules('/' + 'Users/' + 'synthetic'))

    def test_platform_identifiers(self):
        self.assertIn('platform-id', self.rules('GTM-' + 'ABC1234'))
        self.assertIn('shop-domain', self.rules('synthetic' + '.myshopify.com'))

    def test_urls(self):
        self.assertIn('access-bearing-url', self.rules('https://example.invalid/?' + 'token=' + 'synthetic'))
        self.assertIn('unreviewed-url-host', self.rules('https://' + 'private.test/path'))
        self.assertNotIn('unreviewed-url-host', self.rules('https://example.invalid/reference'))

    def test_personal_and_network(self):
        self.assertIn('email', self.rules('person' + '@' + 'private.test'))
        self.assertIn('private-network-address', self.rules('10.' + '20.30.40'))
        self.assertEqual(set(), self.rules('person@example.invalid http://localhost:6006'))

    def test_secret_assignment(self):
        self.assertIn('secret-assignment', self.rules('password' + '="' + 'synthetic-secret-value' + '"'))

    def test_tree_boundary_and_binary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'.git').mkdir()
            (root/'.git'/'config').write_text('gh' + 'p_' + 'A' * 36)
            (root/'safe.md').write_text('https://example.invalid')
            self.assertEqual([], scan_tree(root))
            (root/'raw.bin').write_bytes(b'\x00\xff')
            self.assertIn('non-text-review-required', {x[2] for x in scan_tree(root)})

    def test_filename_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'.env.local').write_text('')
            (root/'pointer').symlink_to('missing')
            rules = {x[2] for x in scan_tree(root)}
            self.assertIn('sensitive-file-type', rules)
            self.assertIn('symlink-review-required', rules)

    def test_private_directory_is_not_a_privacy_exemption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'.local').mkdir()
            (root/'.local'/'note.md').write_text('gh' + 'p_' + 'C' * 36)
            self.assertIn('token', {x[2] for x in scan_tree(root)})

    def test_reports_omit_secret_values(self):
        value = 'gh' + 'p_' + 'B' * 36
        self.assertNotIn(value, repr(scan_text(value)))

if __name__ == '__main__':
    unittest.main()
