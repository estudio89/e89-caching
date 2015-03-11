from django.db.models import get_model
from django.core.cache import cache
import threading
from django.db.models.signals import post_save, post_delete
import sys

def _generate_hash(manager, args = None, kwargs = None):
	if isinstance(manager, BaseCacheManager):
	    return hash(manager.__class__.__name__ + manager._args.__repr__() + manager._kwargs.__repr__())
	else:
		return hash(manager.__name__ + args.__repr__() + kwargs.__repr__())


class BaseCacheManager(object):
	def __init__(self, *args, **kwargs):
		self._args = args
		self._kwargs = kwargs
		self._running_thread = None
		self._id = self.__hash__()
		self._init_events()

	def _init_events(self):
		''' Subscribes to the post_delete and post_save events, in order to rerun the query if needed. '''

		for app_model in self.get_models():
			app, str_model = app_model.split('.')
			model = get_model(app, str_model)
			for event in [post_save, post_delete]:
				event.connect(receiver=self._get_or_run, sender=model, weak=False)

	def _run_wrapper(self):
		''' Wraps the run method in order to save the results in cache before returning them. '''
		result = self.run(*self._args, **self._kwargs)
		version = self.get_version(*self._args, **self._kwargs)
		cache.set(key = self._id, value = result, timeout = None, version = version)
		self._running_thread = None

		return result

	def _get_or_run(self, separate_thread = True, **kwargs):
		''' Gets the results from cache or runs them if needed. If the parameter "separate_thread" is True,
			then the recalculation of the cache will be done in a separate thread and the results will not be
			returned.'''


		if self._running_thread:
			self._running_thread.join()
			return cache.get(key = self._id, version = self.get_version(*self._args, **self._kwargs))

		result = cache.get(key = self._id, version = self.get_version(*self._args, **self._kwargs))
		if result:
			return result
		else:
			if separate_thread:
				self._running_thread = threading.Thread(target = self._run_wrapper)
				self._running_thread.start()
			else:
				return self._run_wrapper()


	def __hash__(self):
		return _generate_hash(self)

	def get_models(self):
		''' This method must return a list of strings with the names of models that when saved or deleted should
			trigger a check in the validity of the cached data. Model names should be written as "app.model". '''

		raise NotImplementedError

	def get_version(self, *args, **kwargs):
		''' This method must return an integer that represents the version of the data in cache. '''

		raise NotImplementedError

	def run(self, *args, **kwargs):
		''' This method must run the operation and return the results that should be stored in cache. '''
		raise NotImplementedError

	@classmethod
	def get(cls, *args, **kwargs):
		''' Method called by the user in order to get the results from cache or not. '''
		return CacheCentral._get(cls,*args,**kwargs)



class CacheCentral(object):
	cache_managers = []

	@staticmethod
	def _get(cls, *args, **kwargs):
		''' Loops through all the existing cache managers, looking for one with the same query parameters.
			If there is one that matches, its results are returned, if not, then a new one is created and
			the results are calculated and saved in cache.'''
		_id = _generate_hash(cls, args, kwargs)
		for manager in CacheCentral.cache_managers:
			if manager._id == _id:
				return manager._get_or_run(separate_thread=False)

		manager = cls(*args, **kwargs)
		CacheCentral.cache_managers.append(manager)
		return manager._get_or_run(separate_thread=False)
