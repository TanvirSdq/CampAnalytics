import sys
import os
import threading
from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound, MethodNotAllowed
from werkzeug.test import Client
import jinja2

_request_ctx = threading.local()

class _RequestProxy:
    def __getattr__(self, name):
        req = getattr(_request_ctx, 'request', None)
        if req is None:
            raise RuntimeError("Working outside of request context.")
        return getattr(req, name)

request = _RequestProxy()

class Request(WerkzeugRequest):
    pass

class Response(WerkzeugResponse):
    default_mimetype = 'text/html'

def render_template(template_name, **context):
    app = getattr(_request_ctx, 'app', None)
    if app is None:
        raise RuntimeError("Working outside of application context.")
    return app.render_template(template_name, **context)

def redirect(location, code=302):
    response = Response('', status=code)
    response.headers['Location'] = location
    return response

def url_for(endpoint, **values):
    app = getattr(_request_ctx, 'app', None)
    if app is None:
        raise RuntimeError("Working outside of application context.")
    adapter = getattr(_request_ctx, 'url_adapter', None)
    if adapter:
        try:
            return adapter.build(endpoint, values, force_external=False)
        except Exception:
            pass
    for rule in app.url_map.iter_rules():
        if rule.endpoint == endpoint:
            path = rule.rule
            for k, v in values.items():
                path = path.replace(f"<{k}>", str(v))
            return path
    return f"/{endpoint}"

class TestResponse:
    def __init__(self, response):
        self._resp = response
        self.status_code = response.status_code
        self.headers = response.headers
        self.data = response.get_data()

    def get_data(self, as_text=False):
        d = self._resp.get_data()
        if as_text:
            return d.decode('utf-8', errors='replace')
        return d

    @property
    def text(self):
        return self.get_data(as_text=True)

class FlaskClient(Client):
    def open(self, *args, **kwargs):
        # Handle form data passed via data dict in tests
        resp = super().open(*args, **kwargs)
        return TestResponse(resp)

class Flask:
    def __init__(self, import_name, template_folder='templates', static_folder='static'):
        self.import_name = import_name
        self.root_path = os.path.abspath(os.path.dirname(sys.modules[import_name].__file__)) if import_name in sys.modules and hasattr(sys.modules[import_name], '__file__') else os.getcwd()
        self.template_folder = os.path.join(self.root_path, template_folder)
        self.static_folder = os.path.join(self.root_path, static_folder)
        self.url_map = Map()
        self.view_functions = {}
        self.context_processors = []
        self.config = {}
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_folder),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

    def route(self, rule, methods=None, **options):
        if methods is None:
            methods = ['GET']
        def decorator(f):
            endpoint = options.pop('endpoint', f.__name__)
            self.add_url_rule(rule, endpoint, f, methods=methods, **options)
            return f
        return decorator

    def add_url_rule(self, rule, endpoint, view_func, methods=None, **options):
        if methods is None:
            methods = ['GET']
        rule_obj = Rule(rule, endpoint=endpoint, methods=methods, **options)
        self.url_map.add(rule_obj)
        self.view_functions[endpoint] = view_func

    def context_processor(self, f):
        self.context_processors.append(f)
        return f

    def render_template(self, template_name, **context):
        template = self.jinja_env.get_template(template_name)
        ctx = {
            'request': getattr(_request_ctx, 'request', None),
            'config': self.config
        }
        for cp in self.context_processors:
            ctx.update(cp())
        ctx.update(context)
        return template.render(**ctx)

    def wsgi_app(self, environ, start_response):
        req = Request(environ)
        _request_ctx.request = req
        _request_ctx.app = self
        adapter = self.url_map.bind_to_environ(environ)
        _request_ctx.url_adapter = adapter
        try:
            endpoint, values = adapter.match()
            view_func = self.view_functions[endpoint]
            rv = view_func(**values)
            if isinstance(rv, str):
                response = Response(rv, mimetype='text/html')
            elif isinstance(rv, Response):
                response = rv
            elif isinstance(rv, tuple):
                body = rv[0]
                status = rv[1]
                response = Response(body, status=status, mimetype='text/html')
            else:
                response = Response(str(rv), mimetype='text/html')
        except HTTPException as e:
            response = e.get_response(environ)
        except Exception as e:
            response = Response(f"Internal Server Error: {e}", status=500, mimetype='text/plain')
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def test_client(self):
        return FlaskClient(self, Response)

    def run(self, host='127.0.0.1', port=5000, **options):
        from werkzeug.serving import run_simple
        debug = options.pop('debug', None)
        if debug is not None:
            options.setdefault('use_debugger', debug)
            options.setdefault('use_reloader', False)
        run_simple(host, port, self, **options)

__all__ = ["Flask", "Request", "Response", "request", "render_template", "redirect", "url_for"]
