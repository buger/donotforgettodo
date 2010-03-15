from google.appengine.ext import db
from google.appengine.api.labs import taskqueue        

class User(db.Model):
    userid     = db.StringProperty()
    name       = db.StringProperty()
    login_type = db.StringProperty()
        
class Task(db.Model):
    name     = db.StringProperty()
    priority = db.IntegerProperty(default = 8)
    status   = db.IntegerProperty(default = 0)