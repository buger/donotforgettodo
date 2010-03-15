# -*- coding: utf-8 -*-
"""
    Base authentication class for webapp.

    :copyright: 2010 by tipfy.org.
    :license: Apache License Version 2.0. See LICENSE.txt for more details.
"""
from Cookie import BaseCookie
import base64
import calendar
import datetime
import email.utils
import functools
import logging


class RequestAdapter(object):
    """Adapter to transform a `webob` request into a request with the
    attributes expected by `tornado.auth`.

    It must define at least the following attributes or functions:

        request.arguments: a dictionary of GET parameters mapping to a list
                           of values.
        request.host: current request host.
        request.path: current request path.
        request.full_url(): a function returning the current full URL.
    """
    def __init__(self, request):
        """Initializes the request adapter.

        :param request:
            A `webob.Request` instance.
        """
        self.arguments = {}
        for k, v in request.GET.items():
            self.arguments.setdefault(k, []).append(v)

        self.full_url = lambda: request.url
        self.host = request.host
        self.path = request.path


class RequestRedirect(Exception):
    """Exception raised to tell RequestHandler that an HTTP redirect should be
    performed.
    """
    def __init__(self, url):
        Exception.__init__(self)
        self.url = url


class HttpException(Exception):
    """Exception raised for bad requests when performing authentication."""


class WebappAuth(object):
    """Base auth class with common functions used by the mixin classes.

    To use gaema with your favorite framework, you must implement all methods
    from this class. You are free to implement __init__() in a way that
    best fits the framework.
    """
    def __init__(self, handler, **kwargs):
        """Depending on the authentication mixin used, you should provide these
        keyword arguments:

            'google_consumer_key'
            'google_consumer_secret'

            'twitter_consumer_key'
            'twitter_consumer_secret'

            'friendfeed_consumer_key'
            'friendfeed_consumer_secret'

            'facebook_api_key'
            'facebook_secret'
        """
        # Attributes used by the auth mixins (required).
        self.request = RequestAdapter(handler.request)
        self.settings = kwargs

        # Attributes used only internally by this class (specific to the webapp
        # implementation).
        self._request = handler.request
        self._response = handler.response

    def require_setting(name, feature='this feature'):
        """Raises an exception if the given setting is not defined.

        :param name:
            Setting name.
        :param feature:
            Setting description.
        :return:
            `None`.
        """
        if not self.settings.get(name):
            raise Exception('You must define the "%s" setting in your '
                'application to use %s' % (name, feature))

    def async_callback(self, callback, *args, **kwargs):
        """Wraps callbacks with this if they are used on asynchronous requests.

        Catches exceptions and properly finishes the request.

        :param callback:
            Callback function to be wrapped.
        :param args:
            Positional arguments fpr the callback.
        :param kwargs:
            Keyword arguments fpr the callback.
        :return:
            A wrapped callback.
        """
        if callback is None:
            return None

        if args or kwargs:
            callback = functools.partial(callback, *args, **kwargs)

        def wrapper(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception, e:
                logging.error('Exception during callback', exc_info=True)

        return wrapper

    def redirect(self, url):
        """Redirects to the given URL. For webapp, we raise a `RequestRedirect`
        exception and catch it in the `RequestHandler` instance.

        :param url:
            URL to redirect.
        :return:
            `None`.
        """
        raise RequestRedirect(url)

    _ARG_DEFAULT = []
    def get_argument(self, name, default=_ARG_DEFAULT, strip=True):
        """Returns the value of a request GET argument with the given name.

        If default is not provided, the argument is considered to be
        required, and we throw an HTTP 404 exception if it is missing.

        The returned value is always unicode.

        :param:
            Argument name to be retrieved from the request GET.
        :param default:
            Default value to be return if the argument is not in GET.
        :param strip:
            If `True`, returns the value after calling strip() on it.
        :return:
            A request argument, as unicode.
        """
        value = self._request.GET.get(name, default)
        if value is self._ARG_DEFAULT:
            raise HttpException('Missing request argument %s' % name)

        if strip:
            value = value.strip()

        return value

    def get_cookie(self, name, default=None):
        """Gets the value of the cookie with the given name, else default.

        :param:
            Cookie name to be retrieved.
        :param default:
            Default value to be return if cookie is not set.
        :return:
            The cookie value.
        """
        cookie = self._request.cookies.get(name, None)
        if cookie is None:
            return default

        return str(base64.b64decode(cookie))

    def set_cookie(self, name, value, domain=None, expires=None, path='/',
                   expires_days=None):
        """Sets the given cookie name/value with the given options.

        :param name:
            Cookie name.
        :param value:
            Cookie value.
        :param domain:
            Cookie domain.
        :param expires:
            A expiration date as a `datetime` object.
        :param path:
            Cookie path.
        :param expires_days:
            Number of days to calculate expiration.
        :return:
            `None`.
        """
        if expires_days is not None and not expires:
            expires = datetime.datetime.utcnow() + datetime.timedelta(
                days=expires_days)

        cookie = BaseCookie()
        cookie[name] = str(base64.b64encode(value))

        if expires:
            timestamp = calendar.timegm(expires.utctimetuple())
            expires = email.utils.formatdate(timestamp, localtime=False,
                usegmt=True)
            cookie[name]['expires'] = expires

        if path:
            cookie[name]['path'] = path

        if domain:
            cookie[name]['domain'] = domain

        cookie_str = cookie.output()
        if cookie_str.startswith('Set-Cookie:'):
            cookie_str = cookie_str[11:].strip()

        self._response.headers.add_header('Set-Cookie', cookie_str)

