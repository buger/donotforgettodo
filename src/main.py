import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from appengine_utilities.sessions import Session

from models import *

from webapp_auth import WebappAuth, RequestRedirect, HttpException
from gaema import auth

class GoogleAuth(WebappAuth, auth.GoogleMixin):
    pass

         
class BaseHandler(webapp.RequestHandler):
    def render_template(self, filename, **template_vals):
        path = os.path.join(os.path.dirname(__file__), 'templates', filename)
        self.response.out.write(template.render(path, template_vals))


class MainHandler(BaseHandler):
    def get(self):
        session = Session()
        
        try:
            user = session['user']
        except KeyError:
            user = None
        
        if user is not None:        
            tasks = Task.all().ancestor(user).fetch(20)
        else:
            tasks = []
        
        self.render_template("index.html", 
                             user  = user, 
                             tasks = tasks)        
        

class TaskAddHandler(webapp.RequestHandler):
    def post(self):
        session = Session()
        user = session['user']
        
        if user:
            task = Task(parent = user,
                        name   = self.request.get('name'))
            task.put()
        
        self.redirect("/")
        
        
class TaskDeleteHandler(webapp.RequestHandler):
    def get(self, task_key):
        session = Session()
        user = session['user']        

        if user:
            task = Task.get(db.Key(task_key))
            
            # We don't want to delete someone slse's task :)            
            if task.parent().key() == user.key():
                db.delete(task)
        
        self.redirect("/")        


class LoginHandler(BaseHandler):
    def get(self):
        google_auth = GoogleAuth(self)

        try:
            if self.request.GET.get("openid.mode", None):
                google_auth.get_authenticated_user(self._on_auth)
                return

            google_auth.authenticate_redirect()
        except RequestRedirect, e:
            return self.redirect(e.url, permanent=True)

        self.render_template('index.html', user=None)

    def _on_auth(self, user):
        """This function is called immediatelly after an authentication attempt.
        Use it to save the login information in a session or secure cookie.

        :param user:
            A dictionary with user data if the authentication was successful,
            or ``None`` if the authentication failed.
        """
        if user:
            db_user = User.all().filter("login_type", 'google').filter('userid', user['email']).get()
            
            if db_user is None:
                db_user = User(userid     = user['email'], 
                               name       = user['name'],
                               login_type = "google")
                db_user.put()
                
            session = Session()            
            session['user'] = db_user            
        else:
            # Login failed. Show an error message or do nothing.
            pass

        # After cookie is persisted, redirect user to the original URL, using
        # the home page as fallback.
        self.redirect(self.request.GET.get('redirect', '/'))
        

class LogoutHandler(BaseHandler):
    def get(self):
        session = Session()
        
        del session['user']
        
        self.redirect("/", permanent = True)


application = webapp.WSGIApplication([
   ('/', MainHandler),
   ('/create', TaskAddHandler),
   ('/delete/([^\/]*)', TaskDeleteHandler),
   ('/login', LoginHandler),
   ('/logout', LogoutHandler)
   ], debug=True)
                
def main():
    if os.environ.get('SERVER_SOFTWARE') == 'Development/1.0':
        os.environ['USER_IS_ADMIN'] = '1'
    
    run_wsgi_app(application)
 
if __name__ == '__main__':
    main()            
