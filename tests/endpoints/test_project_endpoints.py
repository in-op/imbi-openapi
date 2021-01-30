import json
import uuid

import jsonpatch

from imbi.endpoints import project_links, projects
from tests import base


class AsyncHTTPTestCase(base.TestCaseWithReset):

    ADMIN_ACCESS = True
    TRUNCATE_TABLES = [
        'v1.configuration_systems',
        'v1.data_centers',
        'v1.deployment_types',
        'v1.environments',
        'v1.orchestration_systems',
        'v1.project_link_types',
        'v1.project_types',
        'v1.namespaces'
    ]

    def setUp(self):
        super().setUp()
        self.configuration_system = self.create_configuration_system()
        self.data_center = self.create_data_center()
        self.deployment_type = self.create_deployment_type()
        self.environments = self.create_environments()
        self.namespace_name = str(uuid.uuid4())
        self.namespace = self.create_namespace()
        self.orchestration_system = self.create_orchestration_system()
        self.project_link_type = self.create_project_link_type()
        self.project_type = self.create_project_type()

    def create_configuration_system(self):
        result = self.fetch(
            '/configuration_systems', method='POST', headers=self.headers,
            body=json.dumps({
                'name': str(uuid.uuid4()),
                'description': str(uuid.uuid4()),
                'icon_class': 'fas fa-blind'
            }).encode('utf-8'))
        self.assertEqual(result.code, 200)
        return json.loads(result.body.decode('utf-8'))['name']

    def create_data_center(self):
        result = self.fetch(
            '/data_centers', method='POST', headers=self.headers,
            body=json.dumps({
                'name': str(uuid.uuid4()),
                'description': str(uuid.uuid4()),
                'icon_class': 'fas fa-blind'
            }).encode('utf-8'))
        self.assertEqual(result.code, 200)
        return json.loads(result.body.decode('utf-8'))['name']

    def create_deployment_type(self):
        result = self.fetch(
            '/deployment_types', method='POST', headers=self.headers,
            body=json.dumps({
                'name': str(uuid.uuid4()),
                'description': str(uuid.uuid4()),
                'icon_class': 'fas fa-blind'
            }).encode('utf-8'))
        self.assertEqual(result.code, 200)
        return json.loads(result.body.decode('utf-8'))['name']

    def create_environments(self):
        environments = []
        for iteration in range(0, 2):
            result = self.fetch(
                '/environments', method='POST', headers=self.headers,
                body=json.dumps({
                    'name': str(uuid.uuid4()),
                    'description': str(uuid.uuid4()),
                    'icon_class': 'fas fa-blind'
                }).encode('utf-8'))
            self.assertEqual(result.code, 200)
            environments.append(
                json.loads(result.body.decode('utf-8'))['name'])
        return environments

    def create_orchestration_system(self):
        result = self.fetch(
            '/orchestration_systems', method='POST', headers=self.headers,
            body=json.dumps({
                'name': str(uuid.uuid4()),
                'description': str(uuid.uuid4()),
                'icon_class': 'fas fa-blind'
            }).encode('utf-8'))
        self.assertEqual(result.code, 200)
        return json.loads(result.body.decode('utf-8'))['name']

    def create_project_link_type(self):
        result = self.fetch(
            '/project_link_types', method='POST', headers=self.headers,
            body=json.dumps({
                'link_type': str(uuid.uuid4()),
                'icon_class': 'fas fa-blind'
            }).encode('utf-8'))
        self.assertEqual(result.code, 200)
        return json.loads(result.body.decode('utf-8'))['id']

    def create_namespace(self):
        result = self.fetch(
            '/namespaces', method='POST', headers=self.headers,
            body=json.dumps({
                'name': self.namespace_name,
                'slug': str(uuid.uuid4().hex),
                'icon_class': 'fas fa-blind',
                'maintained_by': []
            }).encode('utf-8'))
        self.assertEqual(result.code, 200)
        return json.loads(result.body.decode('utf-8'))['id']

    def test_project_lifecycle(self):
        record = {
            'namespace_id': self.namespace,
            'project_type_id': self.project_type,
            'name': str(uuid.uuid4()),
            'slug': str(uuid.uuid4().hex),
            'description': str(uuid.uuid4()),
            'data_center': self.data_center,
            'configuration_system': self.configuration_system,
            'deployment_type': self.deployment_type,
            'orchestration_system': self.orchestration_system,
            'environments': self.environments
        }

        # Create
        result = self.fetch(
            '/projects', method='POST', headers=self.headers,
            body=json.dumps(record).encode('utf-8'))
        self.assertEqual(result.code, 200)
        response = json.loads(result.body.decode('utf-8'))
        url = self.get_url('/projects/{}'.format(response['id']))
        self.assert_link_header_equals(result, url)
        self.assertIsNotNone(result.headers['Date'])
        self.assertIsNone(result.headers.get('Last-Modified', None))
        self.assertEqual(
            result.headers['Cache-Control'], 'public, max-age={}'.format(
                projects.RecordRequestHandler.TTL))
        record.update({
            'id': response['id'],
            'namespace': self.namespace_name,
            'project_type': self.project_type_name,
            'created_by': self.USERNAME[self.ADMIN_ACCESS],
            'last_modified_by': None
        })
        self.assertDictEqual(record, response)

        # PATCH
        updated = dict(record)
        updated['description'] = str(uuid.uuid4())
        patch = jsonpatch.make_patch(record, updated)
        patch_value = patch.to_string().encode('utf-8')

        result = self.fetch(
            url, method='PATCH', body=patch_value, headers=self.headers)
        self.assertEqual(result.code, 200)
        new_value = json.loads(result.body.decode('utf-8'))
        record['description'] = updated['description']
        record['last_modified_by'] = self.USERNAME[self.ADMIN_ACCESS]
        self.assertDictEqual(record, new_value)

        # Patch no change
        result = self.fetch(
            url, method='PATCH', body=patch_value, headers=self.headers)
        self.assertEqual(result.code, 304)

        # GET
        result = self.fetch(url, headers=self.headers)
        self.assertEqual(result.code, 200)
        self.assert_link_header_equals(result, url)
        self.assertIsNotNone(result.headers['Date'])
        self.assertIsNotNone(result.headers['Last-Modified'])
        self.assert_link_header_equals(result, url)
        self.assertEqual(
            result.headers['Cache-Control'], 'public, max-age={}'.format(
                projects.RecordRequestHandler.TTL))

        new_value = json.loads(result.body.decode('utf-8'))
        self.assertDictEqual(record, new_value)

        # DELETE
        result = self.fetch(url, method='DELETE', headers=self.headers)
        self.assertEqual(result.code, 204)

        # GET record should not exist
        result = self.fetch(url, headers=self.headers)
        self.assertEqual(result.code, 404)

        # DELETE should fail as record should not exist
        result = self.fetch(url, method='DELETE', headers=self.headers)
        self.assertEqual(result.code, 404)

    def test_create_with_missing_fields(self):
        record = {
            'namespace_id': self.namespace,
            'project_type_id': self.project_type,
            'name': str(uuid.uuid4()),
            'slug': str(uuid.uuid4().hex),
            'data_center': self.data_center,
            'configuration_system': self.configuration_system,
            'deployment_type': self.deployment_type,
            'orchestration_system': self.orchestration_system,
            'environments': self.environments
        }

        # Create
        result = self.fetch(
            '/projects', method='POST', headers=self.headers,
            body=json.dumps(record).encode('utf-8'))
        self.assertEqual(result.code, 200)
        response = json.loads(result.body.decode('utf-8'))
        url = self.get_url('/projects/{}'.format(response['id']))
        self.assert_link_header_equals(result, url)
        self.assertIsNone(result.headers.get('Last-Modified', None))
        self.assertEqual(
            result.headers['Cache-Control'], 'public, max-age={}'.format(
                projects.RecordRequestHandler.TTL))
        record.update({
            'id': response['id'],
            'namespace': self.namespace_name,
            'project_type': self.project_type_name,
            'created_by': self.USERNAME[self.ADMIN_ACCESS],
            'description': None,
            'last_modified_by': None
        })
        self.assertDictEqual(record, response)

    def test_dependencies(self):
        project_a = {
            'namespace_id': self.namespace,
            'project_type_id': self.project_type,
            'name': str(uuid.uuid4()),
            'slug': str(uuid.uuid4().hex),
            'data_center': self.data_center,
            'configuration_system': self.configuration_system,
            'deployment_type': self.deployment_type,
            'orchestration_system': self.orchestration_system,
            'environments': self.environments
        }
        result = self.fetch(
            '/projects', method='POST', headers=self.headers,
            body=json.dumps(project_a).encode('utf-8'))
        self.assertEqual(result.code, 200)
        project_a = json.loads(result.body.decode('utf-8'))

        project_b = {
            'namespace_id': self.namespace,
            'project_type_id': self.project_type,
            'name': str(uuid.uuid4()),
            'slug': str(uuid.uuid4().hex),
            'data_center': self.data_center,
            'configuration_system': self.configuration_system,
            'deployment_type': self.deployment_type,
            'orchestration_system': self.orchestration_system,
            'environments': self.environments
        }
        result = self.fetch(
            '/projects', method='POST', headers=self.headers,
            body=json.dumps(project_b).encode('utf-8'))
        self.assertEqual(result.code, 200)
        project_b = json.loads(result.body.decode('utf-8'))

        # Create the dependency
        result = self.fetch(
            '/projects/{}/dependencies'.format(project_b['id']),
            method='POST', headers=self.headers,
            body=json.dumps({
                'dependency_id': project_a['id']
            }).encode('utf-8'))
        self.assertEqual(result.code, 200)

        result = self.fetch(
            '/projects/{}/dependencies'.format(project_b['id']),
            method='GET', headers=self.headers)
        self.assertEqual(result.code, 200)
        self.assertListEqual(
            json.loads(result.body.decode('utf-8')),
            [{
                'project_id': project_b['id'],
                'created_by': self.USERNAME[self.ADMIN_ACCESS],
                'dependency_id': project_a['id']
            }])

        result = self.fetch(
            '/projects/{}/dependencies/{}'.format(
                project_b['id'], project_a['id']),
            method='GET', headers=self.headers)
        self.assertEqual(result.code, 200)
        self.assertDictEqual(
            json.loads(result.body.decode('utf-8')),
            {
                'project_id': project_b['id'],
                'created_by': self.USERNAME[self.ADMIN_ACCESS],
                'dependency_id': project_a['id']
            })

        result = self.fetch(
            '/projects/{}/dependencies/{}'.format(
                project_b['id'], project_a['id']),
            method='DELETE', headers=self.headers)
        self.assertEqual(result.code, 204)

        result = self.fetch(
            '/projects/{}/dependencies/{}'.format(
                project_b['id'], project_a['id']),
            method='GET', headers=self.headers)
        self.assertEqual(result.code, 404)

    def test_links(self):
        project_record = {
            'namespace_id': self.namespace,
            'project_type_id': self.project_type,
            'name': str(uuid.uuid4()),
            'slug': str(uuid.uuid4().hex),
            'data_center': self.data_center,
            'configuration_system': self.configuration_system,
            'deployment_type': self.deployment_type,
            'orchestration_system': self.orchestration_system,
            'environments': self.environments
        }

        result = self.fetch(
            '/projects', method='POST', headers=self.headers,
            body=json.dumps(project_record).encode('utf-8'))
        self.assertEqual(result.code, 200)
        response = json.loads(result.body.decode('utf-8'))

        record = {
            'project_id': response['id'],
            'link_type_id': self.project_link_type,
            'url': 'https://github.com/AWeber/Imbi'
        }

        links_url = self.get_url('/projects/{}/links'.format(response['id']))
        url = self.get_url('/projects/{}/links/{}'.format(
            response['id'], self.project_link_type))

        # Create
        result = self.fetch(
            links_url, headers=self.headers, method='POST',
            body=json.dumps(record).encode('utf-8'))
        self.assertEqual(result.code, 200)
        link_record = json.loads(result.body.decode('utf-8'))
        self.assert_link_header_equals(result, url)
        self.assertEqual(
            result.headers['Cache-Control'], 'public, max-age={}'.format(
                project_links.RecordRequestHandler.TTL))
        self.assertEqual(
            link_record['created_by'], self.USERNAME[self.ADMIN_ACCESS])
        self.assertEqual(link_record['url'], record['url'])

        # Get links
        result = self.fetch(links_url, headers=self.headers)
        self.assertEqual(result.code, 200)
        self.assert_link_header_equals(result, links_url)
        records = []
        for row in json.loads(result.body.decode('utf-8')):
            for field in {'created_at', 'last_modified_at'}:
                del row[field]
            records.append(row)
        self.assertListEqual(records, [link_record])

        # PATCH
        updated = dict(record)
        updated['url'] = 'https://gitlab.com/AWeber/Imbi'
        patch = jsonpatch.make_patch(record, updated)
        patch_value = patch.to_string().encode('utf-8')

        result = self.fetch(
            url, method='PATCH', body=patch_value, headers=self.headers)
        self.assertEqual(result.code, 200)
        self.assert_link_header_equals(result, url)
        record = json.loads(result.body.decode('utf-8'))
        for field in {'link_type', 'icon_class'}:
            self.assertIsNotNone(record[field])
            del record[field]
        for field in {'created_by', 'last_modified_by'}:
            del record[field]
        self.assertDictEqual(record, updated)

        # Patch no change
        result = self.fetch(
            url, method='PATCH', body=patch_value, headers=self.headers)
        self.assertEqual(result.code, 304)
        self.assert_link_header_equals(result, url)

        # Get
        result = self.fetch(url, headers=self.headers)
        self.assertEqual(result.code, 200)
        record = json.loads(result.body.decode('utf-8'))
        for field in {'link_type', 'icon_class'}:
            self.assertIsNotNone(record[field])
            del record[field]
        for field in {'created_by', 'last_modified_by'}:
            del record[field]
        self.assertDictEqual(record, updated)

        # Delete
        result = self.fetch(url, method='DELETE', headers=self.headers)
        self.assertEqual(result.code, 204)

        # Get 404
        result = self.fetch(url, headers=self.headers)
        self.assertEqual(result.code, 404)
