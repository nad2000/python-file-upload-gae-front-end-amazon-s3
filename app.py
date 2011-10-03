import cgi, os
import datetime
import urllib
import wsgiref.handlers
import pprint
import simples3
from simples3.gae import AppEngineS3Bucket

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

class S3File:
  bucket = 'nad2000-test'
  access_key='AKIAJHBAZAVUBQINT3ZA'
  secret_key='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'
  _bucket = None

  def get_bucket( self):
    if not( self._bucket):
      self._bucket = AppEngineS3Bucket(
        name = self.bucket,
        access_key = self.access_key,
        secret_key = self.secret_key)
      self.base_url = self._bucket.base_url
    return self._bucket

  def save( self, filename, data, mimetype):
    s = self.get_bucket()
    s.put(
      key=filename,
      data=data,
      mimetype=mimetype,
      acl="public-read" )
    self.file_url = self.base_url+'/'+filename

class UploadEvent(db.Model):
    """Models an individual event entry with an file name, user submitting the file,
    mimetype and date."""
    user = db.UserProperty()
    filename = db.StringProperty()
    mimetype = db.StringProperty()
    date = db.DateTimeProperty(auto_now_add=True)


class MainPage(webapp.RequestHandler):
  def get(self):
    # todo:
    pass

class UploadSample(webapp.RequestHandler):

  def get(self):
    template_values = {
      'file_url': self.request.get('file_url'),
    }
    path = os.path.join(os.path.dirname(__file__), 'upload.html')
    self.response.out.write(template.render(path, template_values))

  def post(self):
    user = users.get_current_user()
    filename = self.request.POST.get('img').filename
    mimetype = self.request.POST.get('img').type
    image = self.request.get("img")

    event = UploadEvent()
    event.user = user
    event.filename = filename
    event.mimetype = mimetype

    image = self.request.get("img")

    if image:
      f = S3File()
      f.save(
        filename=filename,
        mimetype=mimetype,
        data=image)

    event.put()
    redirect_url = '/upload'
    if image:
       redirect_url += '?'+urllib.urlencode({'file_url': f.file_url})
    self.redirect(redirect_url)

app = webapp.WSGIApplication([
  ('/', MainPage),
  ('/upload', UploadSample),
  ('/save', UploadSample)
], debug=True)


def main():
  run_wsgi_app(app)


if __name__ == '__main__':
  main()