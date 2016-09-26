import os
import flaskr
import unittest
import tempfile
import random
import string
import json

class FlaskrTestCase(unittest.TestCase):
	def setUp(self):
		flaskr.app.config['TESTING'] = True
		self.db_fd, flaskr.app.config['DATABASE'] = tempfile.mkstemp()
		self.app = flaskr.app.test_client()

	def tearDown(self):
		os.close(self.db_fd)
		os.unlink(flaskr.app.config['DATABASE'])

	def test_get_mails(self):
		sig = flaskr.make_sig("key")
		rv = self.app.get('/mails?key=key&signature=%s&tag=tag' % sig)
		jj = json.loads(rv.data.decode("utf8"))
		assert jj["response"]["error_code"] == 200
		
	def test_sdd_mail(self):
		def rndstr(n):
			return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))
		sig = flaskr.make_sig("key")
		rv =  self.app.get('/add?from=from%s&to=to%s&text=text%s&key=key&signature=%s' % (rndstr(2), rndstr(4), rndstr(10), sig ))
		jj = json.loads(rv.data.decode("utf8"))
		assert jj["response"]["error_code"] == 200
		
if __name__ == '__main__':
	unittest.main()
