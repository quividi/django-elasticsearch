# -*- coding: utf-8 -*-
from django import get_version
from django.conf import settings
from django.db.models import Model
from django.db.models.signals import (
    class_prepared,
    post_delete,
    post_migrate,
    post_save,
)


from django_elasticsearch.serializers import EsJsonSerializer
from django_elasticsearch.managers import ElasticsearchManager


class EsIndexable(Model):
    """
    Mixin that encapsulate all the indexation logic of a model.
    """
    class Meta:
        abstract = True

    class Elasticsearch:
        index = getattr(settings, 'ELASTICSEARCH_DEFAULT_INDEX', 'django')
        mapping = None
        serializer_class = EsJsonSerializer
        fields = None
        facets_limit = 10
        facets_fields = None
        # http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/search-suggesters-term.html
        suggest_fields = None
        # http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/search-suggesters-completion.html
        completion_fields = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # override the manager because we have an instance now
        self.es = ElasticsearchManager(self)

    def _raise_no_db_operation(self):
        if getattr(self, '_is_es_deserialized', False):
            raise ValueError("""The instance {0} of {1} have been deserialized
            from an elasticsearch source and thus
            it's not safe to save it.""".format(self, self.__class__))

    def save(self, *args, **kwargs):
        self._raise_no_db_operation()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._raise_no_db_operation()
        super().delete(*args, **kwargs)


def add_es_manager(sender, **kwargs):
    # Note: the manager needs to know the subclass
    if issubclass(sender, EsIndexable):
        sender.es = ElasticsearchManager(sender)


class_prepared.connect(add_es_manager)


def es_save_callback(sender, instance, **kwargs):
    # TODO: batch ?! @task ?!
    if not issubclass(sender, EsIndexable):
        return
    instance.es.do_index()


def es_delete_callback(sender, instance, **kwargs):
    if not issubclass(sender, EsIndexable):
        return
    instance.es.delete()


def es_syncdb_callback(sender, app=None, created_models=None, **kwargs):
    if not created_models:
        created_models = list()
    if int(get_version()[2]) > 6:
        models = sender.get_models()
    else:
        models = created_models

    for model in models:
        if issubclass(model, EsIndexable):
            model.es.create_index()


if getattr(settings, 'ELASTICSEARCH_AUTO_INDEX', False):
    # Note: can't specify the sender class because EsIndexable is Abstract,
    # see: https://code.djangoproject.com/ticket/9318
    post_save.connect(es_save_callback)
    post_delete.connect(es_delete_callback)
    post_migrate.connect(es_syncdb_callback)
