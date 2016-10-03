
import unittest
from io import BytesIO
from os.path import join, exists

from sqlalchemy import Column, Integer

from sqlalchemy_media.attachments import File, FileList, FileDict
from sqlalchemy_media.stores import StoreManager
from sqlalchemy_media.tests.helpers import Json, TempStoreTestCase


class CollectionsTestCase(TempStoreTestCase):

    def setUp(self):
        super().setUp()
        self.sample_text_file1 = join(self.stuff_path, 'sample_text_file1.txt')

    def test_file_list(self):

        class Person(self.Base):
            __tablename__ = 'person'
            id = Column(Integer, primary_key=True)
            files = Column(FileList.as_mutable(Json))

        session = self.create_all_and_get_session()

        with StoreManager(session):
            person1 = Person()
            person1.files = FileList()
            person1.files.append(File.create_from(BytesIO(b'simple text 1')))
            person1.files.append(File.create_from(BytesIO(b'simple text 2')))
            person1.files.append(File.create_from(BytesIO(b'simple text 3')))
            session.add(person1)
            session.commit()

            person1 = session.query(Person).one()
            self.assertEqual(len(person1.files), 3)
            for f in person1.files:
                self.assertIsInstance(f, File)
                filename = join(self.temp_path, f.path)
                self.assertTrue(exists(filename))
                self.assertEqual(f.locate(), '%s/%s?_ts=%s' % (self.base_url, f.path, f.timestamp))

            # Overwriting the first file
            first_filename = join(self.temp_path, person1.files[0].path)
            person1.files[0].attach(BytesIO(b'Another simple text.'))
            first_new_filename = join(self.temp_path, person1.files[0].path)
            session.commit()
            self.assertFalse(exists(first_filename))
            self.assertTrue(exists(first_new_filename))

    def test_file_dict(self):

        class Person(self.Base):
            __tablename__ = 'person'
            id = Column(Integer, primary_key=True)
            files = Column(FileDict.as_mutable(Json))

        session = self.create_all_and_get_session()

        with StoreManager(session):
            person1 = Person()
            person1.files = FileDict()
            person1.files['first'] = File.create_from(BytesIO(b'simple text 1'))
            person1.files['second'] = File.create_from(BytesIO(b'simple text 2'))
            person1.files['third'] = File.create_from(BytesIO(b'simple text 3'))
            session.add(person1)
            session.commit()

            person1 = session.query(Person).one()
            self.assertEqual(len(person1.files), 3)
            for f in person1.files.values():
                self.assertIsInstance(f, File)
                filename = join(self.temp_path, f.path)
                self.assertTrue(exists(filename))

            # Overwriting the first file
            first_filename = join(self.temp_path, person1.files['first'].path)
            person1.files['first'].attach(BytesIO(b'Another simple text.'))
            first_new_filename = join(self.temp_path, person1.files['first'].path)
            session.commit()
            self.assertFalse(exists(first_filename))
            self.assertTrue(exists(first_new_filename))


if __name__ == '__main__':
    unittest.main()
