import os

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

from models import *

         
def doRender(handler, tname='index.html', values={}, options = {}):
    temp = os.path.join(
        os.path.dirname(__file__),
        'templates/' + tname)
    if not os.path.isfile(temp):
        return False
    
    # Make a copy of the dictionary and add the path
    template_params = dict(values)
    template_params['path'] = handler.request.path
             
    outstr = template.render(temp, template_params)
                
    if 'render_to_string' in options:
        return outstr
    else:
        handler.response.out.write(outstr)
        return True 


class MainHandler(webapp.RequestHandler):
    def get(self):
        tasks = Task.all().fetch(10)
        
        doRender(self, "index.html", {'tasks': tasks})
        

class TaskAddHandler(webapp.RequestHandler):
    def post(self):
        task = Task(name = self.request.get('name'))
        task.put()
        
        self.redirect("/")
        
        
class TaskDeleteHandler(webapp.RequestHandler):
    def get(self, task_key):
        db.delete(db.Key(task_key))
        
        self.redirect("/")        


application = webapp.WSGIApplication([
   ('/', MainHandler),
   ('/create', TaskAddHandler),
   ('/delete/([^\/]*)', TaskDeleteHandler)
   ], debug=True)
                
def main():
    if os.environ.get('SERVER_SOFTWARE') == 'Development/1.0':
        os.environ['USER_IS_ADMIN'] = '1'
    
    run_wsgi_app(application)
 
if __name__ == '__main__':
    main()            
