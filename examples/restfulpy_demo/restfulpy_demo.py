#! /usr/bin/env python3
import functools
import io
from os.path import join, dirname, abspath

from nanohttp import context, HTTPStatus, json, html, settings, Static
from restfulpy.application import Application
from restfulpy.controllers import RestController
from restfulpy.orm import DeclarativeBase, Field, DBSession, commit, synonym
from sqlalchemy import Unicode, Integer, JSON
from sqlalchemy_media import Image, ImageAnalyzer, ImageValidator, \
    MagicAnalyzer, ContentTypeValidator, StoreManager, FileSystemStore, \
    store_manager
from sqlalchemy_media.constants import KB
from sqlalchemy_media.exceptions import DimensionValidationError, \
    AspectRatioValidationError, MaximumLengthIsReachedError, \
    ContentTypeValidationError
from restfulpy.testing import ApplicableTestCase
from bddrest.authoring import status, response, Update, Remove, when


__version__ = '0.1.0-dev'


here = abspath(dirname(__file__))
avatar_storage = abspath(join(here, 'data/assets'))


class Avatar(Image):
    __pre_processors__ = [
        MagicAnalyzer(),
        ContentTypeValidator([
            'image/jpeg',
            'image/png',
        ]),
        ImageAnalyzer(),
        ImageValidator(
            minimum=(100, 100),
            maximum=(500, 500),
            min_aspect_ratio=1,
            max_aspect_ratio=1,
            content_types=['image/jpeg', 'image/png']
        ),
    ]

    __max_length__ = 50 * KB
    __min_length__ = 1 * KB
    __prefix__ = 'avatar'


class Person(DeclarativeBase):
    __tablename__ = 'person'

    id = Field(Integer, primary_key=True)
    name = Field(Unicode)
    _avatar = Field(
        'avatar',
        Avatar.as_mutable(JSON),
        nullable=True,
        protected=False,
        json='avatar',
        not_none=False,
        label='Avatar',
        required=False,
    )

    def _set_avatar(self, value):
        if value is not None:
           try:
               self._avatar = Avatar.create_from(value)

           except DimensionValidationError as e:
               raise HTTPStatus(f'600 {e}')

           except AspectRatioValidationError as e:
               raise HTTPStatus(f'601 {e}')

           except ContentTypeValidationError as e:
               raise HTTPStatus(f'602 {e}')

           except MaximumLengthIsReachedError as e:
               raise HTTPStatus(f'603 {e}')

        else:
             self._avatar = None

    def _get_avatar(self):
        return self._avatar.locate() if self._avatar else None

    avatar = synonym(
        '_avatar',
        descriptor=property(_get_avatar, _set_avatar),
    )


class MasterPageView(object):
    header = '<!DOCTYPE html><head><meta charset="utf-8"><title>%s</title>'
    '</head><body>'
    footer = '</body>'

    def __init__(self, title='demo', body=''):
        self.title = title
        self.body = body

    def __str__(self):
        return (self.header % self.title) + self.body + self.footer

    def __iadd__(self, other):
        self.body += other if isinstance(other, str) else str(other)
        return self

    def __iter__(self):
        return iter(str(self).splitlines())


class Root(RestController):
    assets = Static(avatar_storage)

    @html
    def get(self):
        page = MasterPageView('Index')
        page += '<form method="POST" action="/" enctype="multipart/form-data">'
        page += '<input type="text" name="name" value="Your Name here"/>'
        page += '<input type="file" name="avatar" />'
        page += '<input type="submit" />'
        page += '</form>'
        return page

    @store_manager(DBSession)
    @html
    @commit
    def post(self):
        person = Person(
            name=context.form.get('name'),
            avatar=context.form.get('avatar')
        )
        DBSession.add(person)
        DBSession.flush()

        page = MasterPageView('View', body='<ul>')
        for p in DBSession.query(Person).all():
            page += '<li>'
            page += '<img src="%s" alt="%s">' % (p.avatar, p.name)
            page += '<h2>%s</h2>' % p.name
            page += '<h2>ID: %s</h2>' % p.id
            page += '</li>'

        page += '</ul>'
        return page


class Restfulpydemo(Application):
    __configuration__ = '''
    db:
      url: postgresql://postgres:postgres@localhost/restfulpy_demo_dev
      test_url: postgresql://postgres:postgres@localhost/restfulpy_demo_test
      administrative_url: postgresql://postgres:postgres@localhost/postgres

    storage:
      local_directory: %(root_path)s/restfulpy_demo/data/assets
      base_url: http://localhost:8080/assets
    '''

    def __init__(self, application_name='restfulpy_demo', root=Root()):
        super().__init__(
            application_name,
            root=root,
            root_path=join(dirname(__file__), '..'),
            version=__version__,
        )

    @classmethod
    def initialize_orm(cls, engine=None):
        StoreManager.register(
            'fs',
            functools.partial(
                FileSystemStore,
                settings.storage.local_directory,
                base_url=settings.storage.base_url,
            ),
            default=True
        )
        super().initialize_orm(cls, engine)


restfulpy_demo = Restfulpydemo()


TEST_DIR = abspath(dirname(__file__))
STUFF_DIR = join(TEST_DIR, 'stuff')
VALID_AVATAR_PATH = join(STUFF_DIR, 'avatar-150x150.jpg')
INVALID_FORMAT_AVATAR_PATH = join(STUFF_DIR, 'test.pdf')
INVALID_MAXIMUM_SIZE_AVATAR_PATH = join(STUFF_DIR, 'avatar-550x550.jpg')
INVALID_MINIMUM_SIZE_AVATAR_PATH = join(STUFF_DIR, 'avatar-50x50.jpg')
INVALID_RATIO_AVATAR_PATH = join(STUFF_DIR, 'avatar-300x200.jpg')
INVALID_MAXMIMUM_LENGTH_AVATAR_PATH = join(STUFF_DIR,
    'avatar-maximum-length.jpg'
)


class TestPerson(ApplicableTestCase):
    __application_factory__ = Restfulpydemo

    def test_post(self):
        with open(VALID_AVATAR_PATH, 'rb') as f, self.given(
            'Creating a person successfully',
            '/',
            'POST',
            multipart=dict(
                name='person 1',
                avatar=io.BytesIO(f.read()),
            )
        ):
            assert status == 200

            with open(INVALID_MAXIMUM_SIZE_AVATAR_PATH, 'rb') as f:
                when(
                    'The avatar size is exceeded the maximum size',
                    multipart=dict(avatar=io.BytesIO(f.read()))
                )
                assert status == 600

            with open(INVALID_MINIMUM_SIZE_AVATAR_PATH, 'rb') as f:
                when(
                    'The avatar size is less than minimum size',
                    multipart=dict(avatar=io.BytesIO(f.read()))
                )
                assert status == 600

            with open(INVALID_RATIO_AVATAR_PATH, 'rb') as f:
                when(
                    'Aspect ratio of the avatar is invalid',
                    multipart=dict(avatar=io.BytesIO(f.read()))
                )
                assert status == 601

            with open(INVALID_FORMAT_AVATAR_PATH, 'rb') as f:
                when(
                    'Format of the avatar is invalid',
                    multipart=dict(avatar=io.BytesIO(f.read()))
                )
                assert status == 602

            with open(INVALID_MAXMIMUM_LENGTH_AVATAR_PATH, 'rb') as f:
                when(
                    'The maxmimum length of avatar is invalid',
                    multipart=dict(avatar=io.BytesIO(f.read()))
                )
                assert status == 603

    def test_get(self):
        with self.given(
            'Getting a html script',
            '/',
            'GET'
        ):
            assert status == 200


if __name__ == '__main__':
    restfulpy_demo.cli_main()

