# E89 - CACHING


The django app **e89-caching** allows for the results of an expensive operation to be saved in cache.

For every operation that you want to be cached, you define a class that has a method that performs the operation and a method that verifies whether the cache is still valid. You can also specify models that, when updated, should trigger a verification of the cached data so that, if the cached data is not valid anymore, the data is recalculated on a separate thread.

With this approach, the data in cache is always up to date, speeding up the application considerably.

## How to use it

In order to use the app, follow the steps:

1) For every operation that you want to be cached, create a subclass of **e89_caching.caching.BaseCacheManager** and implement the following methods:

  - **get_models(self)**: This method must return a list of strings with the names of models that when saved or deleted should trigger a check in the validity of the cached data. Model names should be written as "app.model".

  - **get_version(self, \*args, **kwargs)**: This method must return an integer that represents the version of the data in cache. A good approach for this method is to return and integer representing the most recent date when one of the objects involved in the calculation was last updated. In this situation, if none of the objects were updated (and no objects were created) then the cache will not be recalculated. The parameters received will be the same passed to the run method (see below).

  - **run(self, \*args, **kwargs)**: This method must run the operation and return the results that should be stored in cache. The parameters received will be passed by the user when requesting the data from the cache (see step 3).

2) In your settings.py file, include 'e89_caching' under **INSTALLED_APPS**. You must also configure caching according to https://docs.djangoproject.com/en/1.7/topics/cache/

3) In your code, whenever you need the cached data, you must request it like this:

  `data = MyCacheManager.get(param1, param2)`

With this setup, whenever a change is made to any of the models returned by the method **get_models**, the method **get_version** will be called and, if this method returns a version that is different from the one returned previously when the data was saved in cache, then the cache is recalculated in a separate thread, without affecting the application performance.

If a request for the data (such as by running the code in step 3) is made while the data is being recalculated, the new data is returned as soon as the recalculation is done.

