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
import simplejson as json

def set_trace():
  """
  Support for debugging GAE application.
  Alsternatively you can start debugging running:
  python -m pdb google_appengine/dev_appserver.py <app dir>
  """
  # ignore, if it's not "localhost"
  if os.environ['SERVER_NAME'] != 'localhost':
      return
  import pdb, sys
  debugger = pdb.Pdb(stdin=sys.__stdin__,
      stdout=sys.__stdout__)
  debugger.set_trace(sys._getframe().f_back)

class S3File:
  """Encapsulates S3 storage management"""
  bucket = 'mm.la'
  access_key='AKIAIE4XT3OMSMEGXHZQ'
  secret_key='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'
  _bucket = None

  def get_bucket( self):
    """S3 bucket lazy loading.

    Returns:
      S3 bucket"""
    if not( self._bucket):
      self._bucket = AppEngineS3Bucket(
        name = self.bucket,
        access_key = self.access_key,
        secret_key = self.secret_key)
      self.base_url = self._bucket.base_url
    return self._bucket

  def save( self, filename, data, mimetype):
    """Created S3 file with supplied properties.

    Arguments:
      filename: file name
      data: file content
      mimetype: file MIME type"""
    s = self.get_bucket()
    s.put(
      key=filename,
      data=data,
      mimetype=mimetype,
      acl="public-read" )
    self.file_url = self.base_url+'/'+filename

  def delete(self, filename):
    """Discard file form the S3 bucket."""
    b = self.get_bucket()
    b.delete( filename)

class UploadedFile(db.Model):
  """Models an individual uploaded file."""
  user = db.UserProperty()
  filename = db.StringProperty()
  size = db.IntegerProperty()
  url = db.StringProperty()
  mimetype = db.StringProperty()
  date = db.DateTimeProperty(auto_now_add=True)

class RequestHandler(webapp.RequestHandler):
  """Application Request Handler base. Place for implementation
  of common functions of the application handlers."""
  def render( self, template_name, template_values = None, debug=False):
    """Renders the template with the given dict of values and outputs
    the rendered content to the response.

    Example usage:
      render("index.html", {"name": "Robert Hunt", "values": [1, 2, 3]})

    Arguments:
      template_name: a name of a Django template
      template_values: dictionary of values to apply to the template
      debug: debugging flag
    """
    if not(template_values):
      template_values = {}
    path = os.path.join(os.path.dirname(__file__), template_name )
    self.response.out.write(template.render(path, template_values, debug))

class MainPage(webapp.RequestHandler):
  """Application default handler."""
  def get(self):
    """Redirects to the static page."""
    self.redirect('index.html')

class PyInfoHandler(webapp.RequestHandler):
  """Handler outputs information about the current state of the environment."""
  def get(self):
    for name in os.environ.keys():
      self.response.out.write("%s = %s<br />\n" % (name, os.environ[name]))


class UploadHandler(webapp.RequestHandler):
  """File upload handler."""

  def initialize(self, request, response):
    """webapp.RequestHandler handler initialization extension."""
    webapp.RequestHandler.initialize(self, request, response)
    response.headers.add_header('Pragma', 'no-cache')
    response.headers.add_header('Cache-Control', 'private, no-cache')
    response.headers.add_header('Content-Disposition', 'inline', filename='files.json')
    response.headers.add_header('X-Content-Type-Options', 'nosniff')

  def get_file_objects(self, filename = None):
    """Creats file object for including into JSON feed."""
    file_qry = UploadedFile.all().order('-date')
    if filename:
      file_qry.filter('filename =', filename)
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
    """Retrieves file list or a single file info"""
    filename = self.request.get('file')
    if filename:
      info = self.get_file_objects( filename)
    else:
      info = self.get_file_objects()
    self.response.headers.add_header('Content-type', 'application/json')
    json.dump( info, self.response.out)

  def post(self):
    """Handle file upload:
      - dowload the file;
      - uploads the file to Amazon S3;
      - stores meta data into the store."""
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
      uf.url = f.file_url

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
    """Delete file form the store."""
    filename = self.request.get('file')
    success = (filename != None)
    if success:
      try:
        s3f = S3File()
        s3f.delete( filename=filename )
      except:
        pass
      file_qry = UploadedFile.all().filter('filename =', filename)
      for f in file_qry:
        f.delete()
    self.response.headers.add_header('Content-type', 'application/json')
    json.dump( success, self.response.out)

app = webapp.WSGIApplication([
  ('/', MainPage),
  ('/upload', UploadHandler),
  ('/pyinfo', PyInfoHandler)
], debug=True)


def main():
  run_wsgi_app(app)

if __name__ == '__main__':
  main()
