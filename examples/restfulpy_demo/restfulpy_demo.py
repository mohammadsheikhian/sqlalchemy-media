#! /usr/bin/env python3
import functools
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
            minimum=(200, 200),
            maximum=(700, 700),
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
               raise HTTPStatus(f'618 {e}')

           except AspectRatioValidationError as e:
               raise HTTPStatus(f'619 {e}')

           except ContentTypeValidationError as e:
               raise HTTPStatus(f'620 {e}')

           except MaximumLengthIsReachedError as e:
               raise HTTPStatus(f'621 {e}')

        else:
             self._avatar = None

    def _get_avatar(self):
        return self._avatar.locate() if self._avatar else None

    avatar = synonym(
        '_avatar',
        descriptor=property(_get_avatar, _set_avatar),
    )


class Root(RestController):
    assets = Static(avatar_storage)

    @html
    def get(self):
        page = '<!DOCTYPE html><head><meta charset="utf-8"><title>%s</title></head><body>'
        page = '</body>'
        page += '<form method="POST" action="/" enctype="multipart/form-data">'
        page += '<input type="text" name="name" value="Your Name here"/>'
        page += '<input type="file" name="avatar" />'
        page += '<input type="submit" />'
        page += '</form>'
        return page

    @store_manager(DBSession)
    @json
    @commit
    def post(self):
        person = Person(
            name=context.form.get('name'),
            avatar=context.form.get('avatar')
        )
        DBSession.add(person)
        return person


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


if __name__ == '__main__':
    restfulpy_demo.cli_main()

