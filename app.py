import cgi, os
import datetime
import urllib
import wsgiref.handlers
import pprint
import simples3
from simples3.gae import AppEngineS3Bucket

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp # import webapp2 as webapp #
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
import simplejson as json


def set_trace():
    # ignore, if it's not "localhost"
    if os.environ['SERVER_NAME'] != 'localhost':
        return
    import pdb, sys
    debugger = pdb.Pdb(stdin=sys.__stdin__,
        stdout=sys.__stdout__)
    debugger.set_trace(sys._getframe().f_back)

class S3File:
  bucket = 'mm.la'
  access_key='AKIAIE4XT3OMSMEGXHZQ'
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
  file_url = db.StringProperty()
  mimetype = db.StringProperty()
  date = db.DateTimeProperty(auto_now_add=True)

class UploadedFile(db.Model):
  """Models an individual uploaded file."""
  user = db.UserProperty()
  filename = db.StringProperty()
  size = db.IntegerProperty()
  url = db.StringProperty()
  mimetype = db.StringProperty()
  date = db.DateTimeProperty(auto_now_add=True)

class RequestHandler(webapp.RequestHandler):
  def render( self, template_name, template_values = None):
    path = os.path.join(os.path.dirname(__file__), template_name )
    self.response.out.write(template.render(path, template_values))

class MainPage(webapp.RequestHandler):
  def get(self):
    self.redirect('index.html')

class UploadSample(RequestHandler):

  def get(self):
    upload_query = UploadEvent.all().order('-date')
    uploads = upload_query.fetch(10)
    #set_trace()
    template_values = {
      'file_url': self.request.get('file_url'),
      'uploads': uploads
    }
    self.render( 'upload.html', template_values)

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

    redirect_url = '/upload'
    if image:
       redirect_url += '?'+urllib.urlencode({'file_url': f.file_url})
       event.file_url = f.file_url

    event.put()
    self.redirect(redirect_url)

class PrintEnvironmentHandler(webapp.RequestHandler):
    def get(self):
        for name in os.environ.keys():
            self.response.out.write("%s = %s<br />\n" % (name, os.environ[name]))


class UploadHandler(webapp.RequestHandler):

  def initialize(self, request, response):
    webapp.RequestHandler.initialize(self, request, response)
    response.headers.add_header('Pragma', 'no-cache')
    response.headers.add_header('Cache-Control', 'private, no-cache')
    response.headers.add_header('Content-Disposition', 'inline', filename='files.json')
    response.headers.add_header('X-Content-Type-Options', 'nosniff')
    #from django.utils import simplejson
    #import simplejson as json

  def get_file_objects(self, file_name = None):
    file_qry = UploadedFile.all().order('-date')
    if file_name:
      file_qry.filter('name =', file_name)
    return [
      {
        'name': f.filename,
        'type': f.mimetype,
        'size': f.size,
        'url': f.url,
        'delete_url': self.request.path+'?'+urllib.urlencode({'file': f.filename}),
        'delete_type': 'DELETE'
      }
     for f in file_qry]

  def head(self):
    self.get()

  def get(self):
    "Retrieves file list or a single fine info "
    file = self.request.get('file')
    if file:
      info = self.get_file_objects( file)
    else:
      info = self.get_file_objects()
    self.response.headers.add_header('Content-type', 'application/json')
    json.dump( info, self.response.out)

  def post(self):
    #pprint.pprint(self.request.POST.get('files[]'))
    #return
    user = users.get_current_user()
    filename = self.request.POST.get('files[]').filename
    mimetype = self.request.POST.get('files[]').type
    content = self.request.get('files[]')
    size = len(content)

    uf = UploadedFile()
    uf.user = user
    uf.filename = filename
    uf.miletype = mimetype
    uf.size = size

    if content:
      f = S3File()
      f.save(
        filename=filename,
        mimetype=mimetype,
        data=content)
      uf.file_url = f.file_url

    uf.put()
    json.dump( [{
      'name': filename,
      'type': mimetype,
      'size': size,
      'url': f.file_url,
      'delete_url': self.request.path+'?'+urllib.urlencode({'file': filename}),
      'delete_type': 'DELETE'
    }] , self.response.out )


  def delete(self):
    pass

app = webapp.WSGIApplication([
  ('/', MainPage),
  ('/upload', UploadHandler),
  ('/save', UploadSample),
  ('/pyinfo', PrintEnvironmentHandler)
], debug=True)


def main():
  run_wsgi_app(app)

if __name__ == '__main__':
  main()