# -*- coding: utf-8 -*-

import json

from ..base import Serializer

class CollectionMetaOptions(object):

    def __init__(self, meta):
        self.with_metadata = True
        self.metadata_key = '_metadata'
        self.items_key = 'items'
        self.offset_key = 'offset'
        self.limit_key = 'limit'
        self.total_count_key = 'totalCount'
        self.fields = []
        self.exclude = []
        self.sort = []

        if hasattr(meta, 'with_metadata'):
            self.with_metadata = meta.with_metadata
        if hasattr(meta, 'fields'):
            self.fields[:] = meta.fields
        if hasattr(meta, 'exclude'):
            self.exclude[:] = meta.exclude
        if hasattr(meta, 'sort'):
            self.sort[:] = meta.sort
        if hasattr(meta, 'offset_key'):
            self.offset_key = meta.offset_key
        if hasattr(meta, 'limit_key'):
            self.limit_key = meta.limit_key
        if hasattr(meta, 'total_count_key'):
            self.total_count_key = meta.total_count_key
        if hasattr(meta, 'metadata_key'):
            self.metadata_key = meta.metadata_key
        if hasattr(meta, 'items_key'):
            self.items_key = meta.items_key


class CollectionBase(type):

    def __new__(cls, name, bases, attrs):
        if 'META' in attrs:
            meta = attrs.pop('META')
        else:
            meta = object()
        new_class = super(CollectionBase, cls).__new__(cls, name, bases, attrs)
        setattr(new_class, '_meta', CollectionMetaOptions(meta))
        return new_class


class CollectionSerializer(object):
    ITEM_SERIALIZER_CLS = None

    __metaclass__ = CollectionBase

    class META:
        with_metadata = True
        fields = []
        exclude = []
        sort = []
        metadata_key = '_metadata'
        items_key = 'items'
        offset_key = 'offset'
        limit_key = 'limit'
        total_count_key = 'totalCount'

    def __init__(self, objects, fields=None, exclude=None, sort=None, limit=None, offset=None, **extras):
        if self.ITEM_SERIALIZER_CLS is None or not issubclass(self.ITEM_SERIALIZER_CLS, Serializer):
            raise Exception('No item serializer set')
        self.objects = objects
        self._fields = fields or self._meta.fields
        self._exclude = exclude or self._meta.exclude
        self._sort = sort or self._meta.sort
        self._limit = limit or 10
        self._offset = offset or 0
        self.with_metadata = self._meta.with_metadata
        self._extras = extras
        self.handle_extras(extras=self._extras)

    def handle_extras(self, extras):
        pass

    def metadata(self, objects):
        total_count = len(objects)
        if self._offset > total_count:
            self._offset = total_count
        if self._offset >= total_count:
            self._limit = 0
        _metadata = {}
        _metadata[self._meta.offset_key] = self._offset or 0
        _metadata[self._meta.limit_key] = self._limit or total_count
        _metadata[self._meta.total_count_key] = total_count
        return _metadata

    def item(self, obj):
        return self.ITEM_SERIALIZER_CLS(source=obj, fields=self._fields, exclude=self._exclude, **self._extras).dump()

    def _pre(self, objects, limit=None, offset=None, sort=None):
        if offset is None:
            offset = 0
        try:
            offset = int(offset)
            limit = int(limit)
        except Exception, e:
            limit = None
        if sort is not None or not isinstance(sort, list):
            sort = [str(sort)]
        try:
            if limit:
                objects = objects[offset:(offset + limit)]
        except Exception, e:
            return {}
        else:
            return objects

    def _items(self, objects):
        objects = self._pre(objects=objects, limit=self._limit, offset=self._offset, sort=self._sort)
        return map(lambda o: self.item(obj=o), objects)

    def _generate(self, objects):
        if hasattr(self, 'result'):
            return self.result
        if self.with_metadata:
            self.result = dict()
            self.result[self._meta.metadata_key] = self.metadata(objects)
            self.result[self._meta.items_key] = self._items(objects)
        else:
            self.result = self._items(objects)

    def dump(self):
        self._generate(self.objects)
        return self.result

    def to_json(self, indent=4):
        dump = self.dump()
        return json.dumps(dump, indent=indent)