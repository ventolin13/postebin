from flask import Flask, request, make_response, render_template, redirect
import re
import codecs
import hashlib
import requests
import psycopg2
from datetime import datetime, timedelta
import time
from urllib.parse import quote, unquote

try:
	import json
except ImportError:
	import simplejson as json

app = Flask(__name__)
app.debug = True

AUTH_KEY = {"key" : "secret"}

def make_sig(key, d = {}):
	d = d or {"service" : "pastebin.com",
			"timestamp" : datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
			}
	ds = json.dumps(d)
	h = hashlib.md5(ds.encode("utf8"))
	h.update(AUTH_KEY[key].encode("utf8"))
	q = quote(codecs.encode(h.digest(), "base64").strip())
	return q


def check_sig(key, sig):
	found = False
	if key not in AUTH_KEY : return False
	for i in range(30):
		dt = datetime.now() - timedelta(seconds=i)
		d = {"service" : "pastebin.com",
			"timestamp" : dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
			}
		if make_sig(key, d) == sig:
			found = True
			break
	return found


def ret(mails, error, error_code):
	if error:
		d = {"response":{"mails":mails, "error_code":error_code, "error":error}}
	else:
		d = {"response":{"mails":mails, "error_code":error_code}}
	r = make_response(json.dumps(d), error_code)
	r.headers["Content-Type"] = "application/json"
	return r


@app.route('/add', methods=['GET', 'POST'])
def add():
	if request.method == 'POST':
		key = request.form.get("key", "")
		signature = quote(request.form.get("signature", ""))
		from_f = request.form.get("from", "")
		to_f = request.form.get("to", "")
		text_f = request.form.get("to", "")
		tags = [t.strip() for t in request.form.get("tags", "").split(",")]
	else:
		key = request.args.get("key", "")
		signature = quote(request.args.get("signature", ""))
		from_f = request.args.get("from", "")
		to_f = request.args.get("to", "")
		text_f = request.args.get("to", "")
		tags = [t.strip() for t in request.args.getlist("tags")]
	app.logger.info(repr(tags))
	
	if not(key == "free" and signature == "free" or check_sig(key, signature)):
		app.logger.info(signature)
		app.logger.error("Error auth")
		return ret([], "Ошибка авторизации", 403)

	try:
		conn = psycopg2.connect("""dbname='pastebin' user='postbin' host='localhost' password='postbin'""")
	except Exception as msg:
		app.logger.error(repr(msg))
		return ret([], "Неизвестная ошибка", 404)
	
	cur = conn.cursor()
	tags = '"%s"' % '","'.join(tags) if tags else ""
	c = cur.execute("""INSERT INTO mail (from_f, to_f, time_f, text_f, tags) VALUES ('%s', '%s', CURRENT_TIMESTAMP, '%s', '{%s}');""" % (from_f, to_f, text_f, tags))
	conn.commit()
	return ret([], "", 200)


@app.route('/mails', methods=['GET'])
def mails():
	key = request.args.get("key", "")
	signature = quote(request.args.get("signature", ""))
	limit = request.args.get("limit", 0)
	offset = request.args.get("offset", 0)
	tag = request.args.get("tag", "")
	
	if not(key == "free" and signature == "free" or check_sig(key, signature)):
		app.logger.info(signature)
		app.logger.error("Error auth")
		return ret([], "Ошибка авторизации", 403)
	
	try:
		limit = abs(int(limit))
		offset = abs(int(offset))
	except Exception as msg:
		app.logger.error(repr(msg))
		return ret([], "Неверный формат данных", 404)

	try:
		conn = psycopg2.connect("""dbname='pastebin' user='postbin' host='localhost' password='postbin'""")
	except Exception as msg:
		app.logger.error(repr(msg))
		return ret([], "Неизвестная ошибка", 404)
	
	cur = conn.cursor()
	if not tag:
		if not limit and not offset:
			cur.execute("""SELECT * from mail""")
		elif not limit:
			cur.execute("""SELECT * from mail offset %s""" % (offset))
		elif not offset:
			cur.execute("""SELECT * from mail limit %s""" % (limit))
		else:
			cur.execute("""SELECT * from mail limit %s offset %s""" % (limit, offset))
	else:
		if not limit and not offset:
			cur.execute("""SELECT * from mail where '%s' = any(tags)""" % (tag))
		elif not limit:
			cur.execute("""SELECT * from mail where '%s' = any(tags) offset %s""" % (tag, offset))
		elif not offset:
			cur.execute("""SELECT * from mail where '%s' = any(tags) offset %s""" % (tag, limit))
		else:
			cur.execute("""SELECT * from mail where '%s' = any(tags) limit %s offset %s""" % (tag, limit, offset))
	mails = cur.fetchall()
	
	for i,m in enumerate(mails):
		m = list(m)
		for j,k in enumerate(m):
			if isinstance(k, datetime):
				m[j] = time.mktime(m[j].timetuple())
			elif isinstance(k, str):
				m[j] = m[j].strip()
			elif isinstance(k, list):
				m[j] = [kk.strip() for kk in k]
		mails[i] = list(m)
			
	app.logger.info(repr(mails))
	return ret(mails, "", 200)


if __name__ == '__main__':
	app.run()


#CREATE SEQUENCE mail_ids;

#CREATE TABLE mail (id INTEGER PRIMARY KEY DEFAULT NEXTVAL('mail_ids'), from_f CHAR(64), to_f CHAR(64), time_f timestamp without time zone, text_f text, tags char(256)[]);
