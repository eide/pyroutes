#!/usr/bin/env python
#encoding: utf-8

from pyroutes.http import HttpException, Http404, Http500
from pyroutes.util.request import Request
from pyroutes import settings

from wsgiref.util import shift_path_info
import cgi
import os
import sys
import traceback

global __request__handlers__
__request__handlers__ = {}

def route(path):
    """
    Decorates a function for handling page requests to
    a certain path
    """
    global __request__handlers__

    def decorator(func):
        if path in __request__handlers__:
            raise ValueError("Tried to redefine handler for %s with %s" % \
                    (path, func))
        __request__handlers__[path] = func
    return decorator

def create_request_path(environ):
    """
    Returns a tuple consisting of the individual request parts
    """
    path = shift_path_info(environ)
    request = []
    if not path:
        request = ['/']
    else:
        while path:
            request.append(path)
            path = shift_path_info(environ)
    return request

def find_request_handler(current_path):
    """
    Locates the handler for the specified path. Return None if not found.
    """
    handler = None
    while handler is None:
        if current_path in __request__handlers__:
            handler = __request__handlers__[current_path]
            break
        current_path = current_path[:current_path.rfind("/")]
        if not current_path:
            return None
    return handler

def application(environ, start_response):
    """
    Searches for a handler for a certain request and
    dispatches it if found. Returns 404 if not found.
    """

    request = create_request_path(environ.copy())
    complete_path = '/%s' % '/'.join(request)
    handler = find_request_handler(complete_path)
    if not handler:
        error = Http404()
        if settings.DEBUG:
            response = error.get_response(environ['PATH_INFO'],
                    details="Debug: No handler for path %s" % complete_path)
        else:
            response = error.get_response(environ['PATH_INFO'])
        start_response(response.status_code, response.headers)
        return [response.content]

    try:
        req = Request(environ)
        try:
            response = handler(req)
        except HttpException, e:
            response = e.get_response(environ['PATH_INFO'])
        start_response(response.status_code, response.headers)
        if isinstance(response.content, basestring):
            return [response.content]
        else:
            return response.content
    except Exception, exception:
        error = Http500()
        if settings.DEBUG:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            tb = "".join(traceback.format_exception(exceptionType,
                                                    exceptionValue,
                                                    exceptionTraceback))
            response = error.get_response(
                    environ['PATH_INFO'],
                    description="%s: %s" % (exception.__class__.__name__,
                                            exception),
                    traceback=tb)
        else:
            response = error.get_response(environ['PATH_INFO'])
        start_response(response.status_code, response.headers)
        return [response.content]
