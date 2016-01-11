# -*- coding: utf-8 -*-

import unittest
from datetime import datetime
from decimal import Decimal

from tests.django_tests import django, SKIPTEST_TEXT, TestCase
from tests.django_tests.django_base import (
    TheDjangoModelSerializer, SimpleModelForSerializer, RelOneDjangoModel, RelTwoDjangoModel,
    RelThreeDjangoModel, RelDjangoModelSerializer, RelReverseDjangoModelSerializer)


@unittest.skipIf(django is None, SKIPTEST_TEXT)
class RelDjangoSerializerTests(TestCase):

    def tearDown(self):
        RelOneDjangoModel.objects.all().delete()
        RelTwoDjangoModel.objects.all().delete()
        RelThreeDjangoModel.objects.all().delete()

    @unittest.skip('Reverse relations are not working for now')
    def test_three_level_reverse_relations(self):
        one = RelOneDjangoModel.objects.create(name='Level1')
        two = RelTwoDjangoModel.objects.create(name='Level2', rel_one=one)
        three = RelThreeDjangoModel.objects.create(name='Level3', rel_two=two)
        # from django.db import DEFAULT_DB_ALIAS, connections
        # connection = connections[DEFAULT_DB_ALIAS]
        # import pdb;pdb.set_trace()
        # print len(connection.queries_log)
        # with self.assertNumQueries(0)
        # TODO: serializer has here only id and name, not the reverse relation rel_twos
        serializer = RelReverseDjangoModelSerializer(one)
        self.assertTrue(serializer.is_valid())
        model_dump = serializer.dump()

    def test_three_level_relations(self):
        one = RelOneDjangoModel.objects.create(name='Level1')
        two = RelTwoDjangoModel.objects.create(name='Level2', rel_one=one)
        three = RelThreeDjangoModel.objects.create(name='Level3', rel_two=two)

        with self.assertNumQueries(0):
            serializer = RelDjangoModelSerializer(three)
        with self.assertNumQueries(0):
            self.assertTrue(serializer.is_valid())
        with self.assertNumQueries(0):
            obj_dump = serializer.dump()

        with self.assertNumQueries(3):
            serializer = RelDjangoModelSerializer(RelThreeDjangoModel.objects.first())
        with self.assertNumQueries(0):
            self.assertTrue(serializer.is_valid())
        with self.assertNumQueries(0):
            qs_obj_dump = serializer.dump()

        test_value = {
            'rel_two': {
                'rel_one': {
                    'id': 1,
                    'name': 'Level1'},
                'id': 1,
                'name': 'Level2'},
            'rel_one': None,
            'id': 1,
            'name': 'Level3'
        }
        self.assertDictEqual(obj_dump, test_value)
        self.assertDictEqual(qs_obj_dump, test_value)

    @unittest.skip('Relation exclusion not working for now')
    def test_three_level_relations_with_exclude(self):
        one = RelOneDjangoModel.objects.create(name='Level1')
        two = RelTwoDjangoModel.objects.create(name='Level2', rel_one=one)
        RelThreeDjangoModel.objects.create(name='Level3', rel_two=two)
        # TODO: This should work with only two queries
        with self.assertNumQueries(2):
            serializer = RelDjangoModelSerializer(RelThreeDjangoModel.objects.first(), exclude=['rel_two.rel_one'])
        with self.assertNumQueries(0):
            self.assertTrue(serializer.is_valid())
        with self.assertNumQueries(0):
            model_dump = serializer.dump()


@unittest.skipIf(django is None, SKIPTEST_TEXT)
class FlatSerializerTests(TestCase):
    maxDiff = None

    def tearDown(self):
        SimpleModelForSerializer.objects.all().delete()

    def test_serialize(self):
        values = dict(
            char_field='test',
            integer_field=-23,
            integer_field2=23,
            positiveinteger_field=23,
            float_field=23.23,
            date_field=datetime.strptime('2014-10-07T20:15:23', '%Y-%m-%dT%H:%M:%S').date(),
            datetime_field=datetime.strptime('2014-10-07T20:15:23', '%Y-%m-%dT%H:%M:%S'),
            time_field=datetime.strptime('2014-10-07T20:15:23', '%Y-%m-%dT%H:%M:%S').time(),
            boolean_field=False,
            decimal_field=Decimal('12.12'),
            text_field='test text',
            commaseparatedinteger_field='1,2,3,4',
            choice_field='Zero',
            url_field='http://www.test.test'
        )

        native_values = {
            "float_field": 23.23,
            "url_field": "http://www.test.test",
            "text_field": "test text",
            "time_field": "20:15:23",
            "choice_field": "Linux",
            "char_field": "test",
            "boolean_field": False,
            "integer_field2": 23,
            "commaseparatedinteger_field": "1,2,3,4",
            "id": 1,
            "datetime_field": "2014-10-07T20:15:23",
            "decimal_field": 12.12,
            "date_field": "2014-10-07",
            "integer_field": -23,
            "positiveinteger_field": 23
        }

        simple_model = SimpleModelForSerializer.objects.create(**values)
        serializer = TheDjangoModelSerializer(simple_model)
        values['id'] = simple_model.id
        native_values['id'] = simple_model.id
        self.assertTrue(serializer.is_valid())
        self.assertDictEqual(serializer.to_dict(), values)
        self.assertDictEqual(serializer.dump(), native_values)