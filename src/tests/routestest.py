# encoding: utf-8

import unittest
import minimock
import cgi

from minimock import TraceTracker

import pyroutes


class TestRoute(unittest.TestCase):
    def setUp(self):
        pyroutes.__request__handlers__ = {}
        pyroutes.settings.DEBUG = True

    def tearDown(self):
        minimock.restore()
        reload(cgi)
        reload(pyroutes)

    def createAnonRoute(self, path):
        @pyroutes.route(path)
        def foo(bar, baz):
            pass
        return foo

    def testBasicRoute(self):

        self.createAnonRoute('/')

        self.assertTrue('/' in pyroutes.__request__handlers__)
        self.assertTrue(len(pyroutes.__request__handlers__) == 1)

    def testDoubleRouteException(self):

        self.createAnonRoute('/')
        self.assertRaises(ValueError, self.createAnonRoute, '/')
        self.assertTrue(len(pyroutes.__request__handlers__) == 1)


    def testCreateRequestPath(self):

        self.assertEquals(['foo', 'bar'], pyroutes.create_request_path({'PATH_INFO': '/foo/bar'}))
        self.assertEquals(['foo', 'bar'], pyroutes.create_request_path({'PATH_INFO': '/foo/bar/'}))
        self.assertEquals(['/'], pyroutes.create_request_path({'PATH_INFO': '/'}))
        self.assertEquals(['/'], pyroutes.create_request_path({'PATH_INFO': '//'}))

    def testFindRequestHandler(self):
        self.createAnonRoute('/')
        self.createAnonRoute('/bar')
        self.assertTrue(pyroutes.find_request_handler('/') != None)
        self.assertTrue(pyroutes.find_request_handler('/bar') != None)
        self.assertTrue(pyroutes.find_request_handler('/baz') == None)

    def testApplication404(self):
        environ = {'PATH_INFO': '/foo'}
        tracker = TraceTracker()
        start_response = minimock.Mock('start_response', tracker=tracker)

        response = pyroutes.application(environ, start_response)
        self.assertNotEqual(response[0].find('Debug: No handler for path /foo'), -1)
        self.assertTrue(tracker.check("Called start_response('404 Not Found', [('Content-Type', 'text/html; charset=utf-8')])"))
        pyroutes.settings.DEBUG = False
        response = pyroutes.application(environ, start_response)
        self.assertNotEqual(response[0].find('/foo was not found.'), -1)
        self.assertEqual(response[0].find('Debug: No handler for path /foo'), -1)

    def testApplication200(self):
        environ = {'PATH_INFO': '/'}
        tracker = TraceTracker()
        start_response = minimock.Mock('start_response', tracker=tracker)

        pyroutes.create_data_dict = minimock.Mock('create_data_dict', returns={}, tracker=None)
        res = minimock.Mock('handler', tracker=None)
        res.content = "foobar"
        res.status_code = '200 OK'
        res.headers = [('Content-type', 'text/plain')]

        handler = minimock.Mock('handler', tracker=None, returns=res)

        # Manually inject handler
        pyroutes.__request__handlers__['/'] = handler
        tracker.clear()
        self.assertEquals(["foobar"], pyroutes.application(environ, start_response))
        self.assertTrue(tracker.check("Called start_response('200 OK', [('Content-type', 'text/plain')])"))
        res.content = (1,2,3)
        self.assertEquals((1,2,3), pyroutes.application(environ, start_response))

    def testApplication403(self):
        environ = {'PATH_INFO': '/'}
        tracker = TraceTracker()
        start_response = minimock.Mock('start_response', tracker=tracker)

        pyroutes.create_data_dict = minimock.Mock('create_data_dict', returns={}, tracker=None)
        handler = minimock.Mock('handler', tracker=None)
        handler.mock_raises = pyroutes.http.Http403
        pyroutes.__request__handlers__['/'] = handler
        tracker.clear()
        response = pyroutes.application(environ, start_response)
        self.assertNotEqual(response[0].find('403 Forbidden'), -1)
        self.assertTrue(tracker.check("Called start_response('403 Forbidden', [('Content-Type', 'text/html; charset=utf-8')])"))

    def testApplication500(self):
        environ = {'PATH_INFO': '/'}
        tracker = TraceTracker()
        start_response = minimock.Mock('start_response', tracker=tracker)

        pyroutes.create_data_dict = minimock.Mock('create_data_dict', returns={}, tracker=None)
        handler = minimock.Mock('handler', tracker=None)
        handler.mock_raises = ValueError("foo")
        pyroutes.__request__handlers__['/'] = handler
        tracker.clear()
        response = pyroutes.application(environ, start_response)
        self.assertNotEqual(response[0].find('ValueError: foo'), -1)
        self.assertNotEqual(response[0].find('Server error at /.'), -1)
        self.assertTrue(tracker.check("Called start_response('500 Server Error', [('Content-Type', 'text/html; charset=utf-8')])"))

        pyroutes.settings.DEBUG = False
        response = pyroutes.application(environ, start_response)
        self.assertEqual(response[0].find('ValueError: foo'), -1)
        self.assertNotEqual(response[0].find('Server error at /.'), -1)
