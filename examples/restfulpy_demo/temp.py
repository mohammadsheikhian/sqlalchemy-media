#class FooController(ModelRestController):
#    __model__ = Foo
#
#    @json(prevent_empty_form=True)
#    @Foo.validate(strict=True)
#    @Foo.expose
#    @commit
#    def create(self):
#        title = context.form.get('title')
#
#        if DBSession.query(Foo).filter(Foo.title == title).count():
#            raise HTTPStatus('604 Title Is Already Registered')
#
#        foo = Foo()
#        foo.update_from_request()
#        DBSession.add(foo)
#        return foo
#
#    @json(prevent_empty_form=True)
#    @Foo.validate
#    @Foo.expose
#    @commit
#    def edit(self, id):
#
#        foo = DBSession.query(Foo) \
#            .filter(Foo.id == id) \
#            .one_or_none()
#
#        if foo is None:
#            raise HTTPNotFound(f'Foo with id: {id} is not registered')
#
#        foo.update_from_request()
#        return foo
#
#    @json(prevent_form=True)
#    @Foo.expose
#    @commit
#    def get(self, id=None):
#        if id is None:
#            return DBSession.query(Foo)
#
#        foo = DBSession.query(Foo) \
#            .filter(Foo.id == id) \
#            .one_or_none()
#
#        if foo is None:
#            raise HTTPNotFound(f'Foo with id: {id} is not registered')
#
#        return foo
#
#    @json(prevent_form=True)
#    @Foo.expose
#    @commit
#    def delete(self, id):
#
#        foo = DBSession.query(Foo) \
#            .filter(Foo.id == id) \
#            .one_or_none()
#
#        if foo is None:
#            raise HTTPNotFound(f'Foo with id: {id} is not registered')
#
#        DBSession.delete(foo)
#        return foo
#
#    @json(prevent_form=True)
#    @Foo.expose
#    @commit
#    def list(self):
#        return DBSession.query(Foo)

class TestFoo(ApplicableTestCase):
    __application_factory__ = Restfulpydemo

    @classmethod
    def mockup(cls):
        session = cls.create_session()
        # Adding 5 Foos
        for i in range(5):
            session.add(Foo(title=f'Foo {i}'))

        session.commit()

    def test_foo_crud(self):
        # Creating a new Foo!
        with self.given(
            'Create a new Foo',
            '/foos',
            'CREATE',
            form=dict(title='First foo')
        ):
            assert status == 200
            assert 'title' in response.json
            assert response.json['title'] == 'First foo'
            assert response.json['createdAt'] is not None
            assert response.json['modifiedAt'] is None
            foo_id = response.json['id']

            # Edit it!
            when(
                'Updating the title',
                f'/foos/id: {foo_id}',
                'EDIT',
                form=given | dict(title='First foo(edited)')
            )
            assert status == 200
            assert response.json['title'] == 'First foo(edited)'
            assert response.json['modifiedAt'] is not None

            # Get it!
            when(
                'Retrieve the first foo',
                f'/foos/id: {foo_id}',
                'GET'
            )

            assert status == 200
            assert response.json['title'] == 'First foo(edited)'
            assert response.json['id'] == foo_id

            # Delete it!
            when(
                'Removing the first foo',
                f'/foos/id: {foo_id}',
                'DELETE',
                form=None
            )

            assert status == 200
            assert response.json['title'] == 'First foo(edited)'
            assert response.json['id'] == foo_id

            # Get it again to ensure it removed
            when(
                'Retrieve the first foo',
                f'/foos/id: {foo_id}',
                'GET'
            )

            assert status == 404

    def test_foo_list(self):
        # Listing all foos
        with self.given(
            'Listing all Foos',
            '/foos',
            'LIST',
        ):
            assert status == 200
            assert len(response.json) >= 5

            when(
                'Paginating',
                query=dict(take=1, skip=2, sort='id')
            )
            assert status == 200
            assert len(response.json) == 1
            assert response.json[0]['title'] == 'Foo 2'



