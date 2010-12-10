from bson import ObjectId
import formencode as fe
from formencode import validators as fev

class Ming(fev.FancyValidator):

    def __init__(self, cls, **kw):
        self.cls = cls
        super(Ming, self).__init__(**kw)

    def _to_python(self, value, state):
        result = self.cls.query.get(_id=value)
        if result is None:
            try:
                result = self.cls.query.get(_id=ObjectId(value))
            except:
                pass
        return result

    def _from_python(self, value, state):
        return value._id

class UniqueOAuthApplicationName(fev.UnicodeString):

    def _to_python(self, value, state):
        from allura import model as M
        app = M.OAuthConsumerToken.query.get(name=value)
        if app is not None:
            raise fe.Invalid('That name is already taken, please choose another', value, state)
        return value
