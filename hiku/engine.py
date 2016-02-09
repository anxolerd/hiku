from functools import partial
from itertools import chain
from collections import defaultdict

from . import query
from .graph import Link, Edge
from .result import Result
from .executors.queue import Workflow, Queue


def edge_split(edge, pattern):
    assert isinstance(edge, Edge), repr(edge)
    assert isinstance(pattern, query.Edge), repr(pattern)

    fields = []
    links = []
    edges = []

    for item in pattern.fields.values():
        if isinstance(item, query.Field):
            fields.append((edge.fields[item.name], item))
        elif isinstance(item, query.Link):
            field = edge.fields[item.name]
            if isinstance(field, Link):
                if field.requires:
                    fields.append((edge.fields[field.requires],
                                   query.Field(field.requires)))
                links.append((field, item))
            elif isinstance(field, Edge):
                edges.append(item)
            else:
                raise ValueError('Unexpected edge member: {!r} ({})'
                                 .format(field, item.name))
        else:
            raise ValueError('Unexpected value: {!r}'.format(item))

    return fields, links, edges


def store_fields(result, edge, fields, ids, query_result):
    names = [f.name for f in fields]
    if edge.name is not None:
        if ids is not None:
            for i, row in zip(ids, query_result):
                result.idx[edge.name][i].update(zip(names, row))
        else:
            result[edge.name].update(zip(names, query_result))
    else:
        result.update(zip(names, query_result))


def link_reqs(result, edge, link, ids):
    if edge.name is not None:
        if ids is not None:
            return [result.idx[edge.name][i][link.requires] for i in ids]
        else:
            return result[edge.name][link.requires]
    else:
        return result[link.requires]


def link_ref(result, link, ident):
    return result.ref(link.entity, ident)


def link_refs(result, link, idents):
    return [result.ref(link.entity, i) for i in idents]


def store_links(result, edge, link, ids, query_result):
    field_val = partial(link_refs if link.to_list else link_ref,
                        result, link)
    if edge.name is not None:
        if ids is not None:
            for i, res in zip(ids, query_result):
                result.idx[edge.name][i][link.name] = field_val(res)
        else:
            result[edge.name][link.name] = field_val(query_result)
    else:
        result[link.name] = field_val(query_result)


def link_result_to_ids(is_list, to_list, result):
    if is_list and to_list:
        return list(chain.from_iterable(result))
    elif is_list or to_list:
        return result
    else:
        return [result]


class Query(Workflow):

    def __init__(self, queue, task_set, root):
        self._queue = queue
        self._task_set = task_set
        self.root = root
        self._result = Result()

    def result(self):
        return self._result

    def process_edge(self, edge, pattern, ids):
        fields, links, edges = edge_split(edge, pattern)

        assert not (edge.name and edges), 'Nested edges are not supported yet'
        for link in edges:
            self.process_edge(edge.fields[link.name], link.edge, None)

        to_func = {}
        from_func = defaultdict(list)
        for graph_field, query_field in fields:
            to_func[graph_field.name] = graph_field.func
            from_func[graph_field.func].append(query_field)

        # schedule fields resolve
        to_fut = {}
        for func, func_fields in from_func.items():
            if getattr(func, '__subquery__', None):
                task_set = self._queue.fork(self._task_set)
                if ids is not None:
                    result_proc = func(self._queue, task_set, edge, func_fields,
                                       ids)
                else:
                    result_proc = func(self._queue, task_set, edge, func_fields)
                to_fut[func] = task_set
                self._queue.add_callback(task_set, (
                    lambda:
                    result_proc(self._result)
                ))
            else:
                if ids is not None:
                    fut = self._task_set.submit(func, func_fields, ids)
                else:
                    fut = self._task_set.submit(func, func_fields)
                to_fut[func] = fut
                self._queue.add_callback(fut, (
                    lambda _fut=fut, _func_fields=func_fields:
                    store_fields(self._result, edge, _func_fields, ids,
                                 _fut.result())
                ))

        # schedule link resolve
        for graph_link, query_link in links:
            if graph_link.requires:
                fut = to_fut[to_func[graph_link.requires]]
                self._queue.add_callback(fut, (
                    lambda _gl=graph_link, _ql=query_link:
                    self._process_edge_link(edge, _gl, _ql, ids)
                ))
            else:
                # TODO: validate query_link.options according to the
                # graph_link.options
                if graph_link.options:
                    fut = self._task_set.submit(graph_link.func,
                                                query_link.options)
                else:
                    fut = self._task_set.submit(graph_link.func)
                self._queue.add_callback(fut, (
                    lambda _fut=fut, _gl=graph_link, _qe=query_link.edge:
                    self.process_link(edge, _gl, _qe, ids, _fut.result())
                ))

    def _process_edge_link(self, edge, graph_link, query_link, ids):
        reqs = link_reqs(self._result, edge, graph_link, ids)
        # TODO: validate query_link.options according to the
        # graph_link.options
        if graph_link.options:
            fut = self._task_set.submit(graph_link.func, reqs,
                                        query_link.options)
        else:
            fut = self._task_set.submit(graph_link.func, reqs)
        self._queue.add_callback(fut, (
            lambda:
            self.process_link(edge, graph_link, query_link.edge, ids,
                              fut.result())
        ))

    def process_link(self, edge, graph_link, query_edge, ids, result):
        store_links(self._result, edge, graph_link, ids, result)
        to_ids = link_result_to_ids(ids is not None, graph_link.to_list, result)
        self.process_edge(self.root.fields[graph_link.entity], query_edge,
                          to_ids)


class Engine(object):

    def __init__(self, executor):
        self.executor = executor

    def execute(self, root, pattern):
        queue = Queue(self.executor)
        task_set = queue.fork(None)
        q = Query(queue, task_set, root)
        q.process_edge(q.root, pattern, None)
        return self.executor.process(queue, q)
