# -*- coding: utf-8 -*-
import inspect

from aserializer.utils import py2to3
from aserializer.base import Serializer, SerializerBase
from aserializer import fields as serializer_fields
# from aserializer.django.utils import get_related_model_from_field, is_relation_field, get_fields, \
#     get_related_model_classes

from aserializer.django import utils as django_utils
from aserializer.django.fields import RelatedManagerListSerializerField

try:
    from django.db import models as django_models
    model_field_mapping = {
        django_models.AutoField: serializer_fields.IntegerField,
        django_models.FloatField: serializer_fields.FloatField,
        django_models.PositiveIntegerField: serializer_fields.PositiveIntegerField,
        django_models.SmallIntegerField: serializer_fields.IntegerField,
        django_models.PositiveSmallIntegerField: serializer_fields.PositiveIntegerField,
        django_models.IntegerField: serializer_fields.IntegerField,
        django_models.DateTimeField: serializer_fields.DatetimeField,
        django_models.DateField: serializer_fields.DateField,
        django_models.TimeField: serializer_fields.TimeField,
        django_models.DecimalField: serializer_fields.DecimalField,
        django_models.EmailField: serializer_fields.EmailField,
        django_models.CharField: serializer_fields.StringField,
        django_models.URLField: serializer_fields.UrlField,
        django_models.SlugField: serializer_fields.StringField,
        django_models.TextField: serializer_fields.StringField,
        django_models.CommaSeparatedIntegerField: serializer_fields.StringField,
        django_models.BooleanField: serializer_fields.BooleanField,
        django_models.NullBooleanField: serializer_fields.BooleanField,
    }
except ImportError:
    django_models = None
    model_field_mapping = {}


class DjangoModelSerializerBase(SerializerBase):

    def __new__(cls, name, bases, attrs):
        new_class = super(DjangoModelSerializerBase, cls).__new__(cls, name, bases, attrs)
        cls.set_fields_from_model(new_class=new_class,
                                  fields=new_class._base_fields,
                                  meta_options=new_class._meta)
        return new_class

    @staticmethod
    def get_all_fieldnames(fields):
        result = []
        for name, field in fields.items():
            result.append(name)
            if field.map_field:
                result.append(field.map_field)
        return list(set(result))

    @classmethod
    def set_fields_from_model(cls, new_class, fields, meta_options):
        setattr(new_class, 'model_fields', [])
        if django_models is None or meta_options.model is None:
            return
        all_field_names = cls.get_all_fieldnames(fields)
        for model_field in django_utils.get_local_fields(meta_options.model):
            if model_field.name not in all_field_names:
                if cls.add_local_model_field(fields, model_field):
                    new_class.model_fields.append(model_field.name)
        for model_field in django_utils.get_related_fields(meta_options.model):
            if cls.add_relation_model_field(fields, model_field, meta_options=meta_options):
                new_class.model_fields.append(model_field.name)
        for model_field in django_utils.get_reverse_related_fields(meta_options.model):
            if cls.add_reverse_relation_model_field(fields, model_field, meta_options=meta_options):
                new_class.model_fields.append(model_field.name)

    @staticmethod
    def get_field_class(model_field, mapping=None):
        if mapping is None:
            mapping = model_field_mapping
        for model in inspect.getmro(model_field.__class__):
            if model in mapping:
                return mapping[model]
        return None

    @staticmethod
    def get_nested_serializer_class(model_field, parent_manager=None, **kwargs):
        class NestedModelSerializer(NestedDjangoModelSerializer):
            class Meta:
                model = model_field
                parents = parent_manager
        return NestedModelSerializer

    @classmethod
    def get_field_from_modelfield(cls, model_field, **kwargs):
        field_class = cls.get_field_class(model_field)
        if model_field.primary_key:
            kwargs['identity'] = True
            kwargs['required'] = False
            kwargs['on_null'] = serializer_fields.HIDE_FIELD
        if model_field.null:
            kwargs['required'] = False
        if model_field.has_default():
            kwargs['default'] = model_field.get_default()
        if model_field.flatchoices:
            kwargs['choices'] = model_field.flatchoices
            return serializer_fields.ChoiceField(**kwargs)
        if isinstance(model_field, django_models.CharField) and not isinstance(model_field, django_models.URLField):
            max_length = getattr(model_field, 'max_length', None)
            if max_length is not None:
                kwargs.update({'max_length': getattr(model_field, 'max_length')})
        elif isinstance(model_field, django_models.DecimalField):
            kwargs.update({'decimal_places': getattr(model_field, 'decimal_places')})
        return field_class(**kwargs) if field_class else None

    @classmethod
    def add_local_model_field(cls, fields, model_field, **kwargs):
        _field = cls.get_field_from_modelfield(model_field, **kwargs)
        if _field is None:
            return False
        _field.add_name(model_field.name)
        fields[model_field.name] = _field
        return True

    @classmethod
    def add_relation_model_field(cls, fields, model_field, meta_options, **kwargs):
        if django_utils.is_relation_field(model_field):
            rel_django_model = django_utils.get_related_model_from_field(model_field)
            if meta_options.parents.ignore_child(meta_options.model, rel_django_model):
                return False
            meta_options.parents.add(meta_options.model, rel_django_model)
            if model_field.primary_key:
                kwargs['identity'] = True
                kwargs['required'] = False
                kwargs['on_null'] = serializer_fields.HIDE_FIELD
            if model_field.null or model_field.blank:
                kwargs['required'] = False
            serializer_cls = cls.get_nested_serializer_class(rel_django_model, meta_options.parents)
            if isinstance(model_field , django_models.ManyToManyField):
                _field = RelatedManagerListSerializerField(serializer_cls, **kwargs)
            else:
                _field = serializer_fields.SerializerField(serializer_cls, **kwargs)
            _field.add_name(model_field.name)
            fields[model_field.name] = _field
            return True
        return False

    @classmethod
    def add_reverse_relation_model_field(cls, fields, model_field, meta_options, **kwargs):
        if isinstance(model_field, django_utils.get_related_model_classes()):
            rel_django_model = django_utils.get_related_model_from_field(model_field)
            if meta_options.parents.ignore_child(meta_options.model, rel_django_model):
                return
            serializer_cls = cls.get_nested_serializer_class(rel_django_model, meta_options.parents)
            if isinstance(model_field, django_models.OneToOneRel):
                _field = serializer_fields.SerializerField(serializer_cls, required=False, **kwargs)
            else:
                _field = RelatedManagerListSerializerField(serializer_cls, required=False, **kwargs)
            _field.add_name(model_field.name)
            fields[model_field.name] = _field
            return True
        return False


class NestedDjangoModelSerializer(py2to3.with_metaclass(DjangoModelSerializerBase, Serializer)):
    with_registry = False


class DjangoModelSerializer(py2to3.with_metaclass(DjangoModelSerializerBase, Serializer)):
    pass
