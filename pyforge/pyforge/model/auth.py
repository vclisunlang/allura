from base64 import b64encode
from random import randint
from hashlib import sha256

from pylons import c

from ming import Document, Session, Field
from ming import schema as S

from .session import ProjectSession

SALT_LENGTH=8

def encode_password(password, salt=None):
    if salt is None:
        salt = ''.join(chr(randint(1, 0x7f))
                       for i in xrange(SALT_LENGTH))
    hashpass = sha256(salt + password.encode('utf-8')).digest()
    return 'sha256' + salt + b64encode(hashpass)

class User(Document):
    SALT_LEN=8
    class __mongometa__:
        name='user'
        session = Session.by_name('main')

    _id=Field(S.ObjectId)
    username=Field(str)
    display_name=Field(str)
    open_ids=Field([str])
    password=Field(str)

    def role_iter(self):
        yield ProjectRole.m.get(name='*anonymous')
        if self._id:
            yield ProjectRole.m.get(name='*authenticated')
        if self._id:
            pr = self.project_role()
            for role in pr.role_iter():
                yield role

    def project_role(self):
        obj = ProjectRole.m.get(user_id=self._id)
        if obj is None:
            obj = ProjectRole.make(dict(user_id=self._id))
            obj.m.save()
        return obj

    def set_password(self, password):
        self.password = encode_password(password)

    def validate_password(self, password):
        if not self.password: return False
        salt = str(self.password[6:6+self.SALT_LEN])
        check = encode_password(password, salt)
        return check == self.password

    def register_project(self, pid):
        from .project import Project
        p = Project.make(dict(
                _id=pid + '/', name=pid,
                database='project:%s' % pid,
                is_root=True))
        c.project = p
        pr = self.project_role()
        for roles in p.acl.itervalues():
            roles.append(pr._id)
        ProjectRole.make(dict(name='*anonymous')).m.save()
        ProjectRole.make(dict(name='*authenticated')).m.save()
        p.install_app('admin', 'admin')
        p.m.insert()
        return p

User.anonymous = User.make(dict(
        _id=None, username='*anonymous', display_name='Anonymous Coward'))

class ProjectRole(Document):
    class __mongometa__:
        session = ProjectSession(Session.by_name('main'))
        name='user'
    
    _id = Field(S.ObjectId)
    name = Field(str)
    user_id = Field(S.ObjectId, if_missing=None) # if role is a user
    roles = Field([S.ObjectId])

    @classmethod
    def for_user(cls, user):
        obj = cls.m.get(user_id=user._id)
        if obj is None:
            obj = cls.make(user_id=user._id)
            obj.m.save()
        return obj

    @property
    def user(self):
        return User.m.get(_id=self.user_id)

    def role_iter(self, visited=None):
        if visited is None: visited = set()
        if self._id not in visited: 
            yield self
            visited.add(self._id)
            for rid in self.roles:
                pr = ProjectRole.m.get(_id=rid)
                if pr is None: continue
                for rr in pr.role_iter(visited):
                    yield rr

